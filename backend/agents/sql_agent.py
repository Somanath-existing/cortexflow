from langchain_core.messages import HumanMessage, SystemMessage
from backend.agents.state import AgentState
from backend.mcp.client import mcp_client
from backend.core.llm import get_llm
import re

llm = get_llm("sql")

SQL_SYSTEM = """You are a SQL expert agent with access to a PostgreSQL business database.

Database contains these key tables:
- customers (customer_id, company_name, contact_name, country, city, region)
- products (product_id, product_name, category, unit_price, units_in_stock)
- orders (order_id, customer_id, order_date, shipped_date, total_amount)
- regional_sales (id, region, state, quarter, year, revenue, units_sold, product_category)
- customer_health (customer_id, health_score, churn_risk, last_order_days_ago, revenue_trend)

Rules for writing SQL:
- Only write SELECT queries — no INSERT, UPDATE, DELETE, DROP
- Always include relevant columns, not SELECT *
- Include ORDER BY for trend analysis
- Use LIMIT 50 max
- For revenue comparisons: GROUP BY state, quarter, year

After running the query, interpret the results clearly with specific numbers.
Put your SQL inside ```sql ... ``` code blocks."""


async def sql_agent_node(state: AgentState) -> dict:
    current_step = state["current_step"]
    plan = state.get("plan", [])

    if current_step >= len(plan):
        return {"current_step": current_step + 1}

    task = plan[current_step]

    # Get schema from MCP
    try:
        schema = await mcp_client.call_tool("database", "get_schema", {})
    except Exception as e:
        schema = f"Schema unavailable: {e}"

    response = await llm.ainvoke([
        SystemMessage(content=SQL_SYSTEM),
        HumanMessage(content=f"""Task: {task}
Original question: {state['user_query']}

Database schema:
{schema}

Write a SQL SELECT query to answer this task, then interpret the results.
Put SQL inside ```sql ... ``` blocks.""")
    ])

    # Strip <think> tags from reasoning models
    raw_content = re.sub(r'<think>.*?</think>', '', response.content, flags=re.DOTALL).strip()

    # Extract and execute SQL
    sql_match = re.search(r'```sql\n(.*?)\n```', raw_content, re.DOTALL)

    query_result = None
    sql_used = None
    if sql_match:
        sql_used = sql_match.group(1).strip()
        try:
            query_result = await mcp_client.call_tool(
                "database",
                "query_database",
                {"sql": sql_used}
            )
        except Exception as e:
            query_result = f"Query error: {str(e)}"

    tool_results = list(state.get("tool_results", []))
    tool_results.append({
        "step": current_step,
        "task": task,
        "agent": "sql_agent",
        "analysis": raw_content[:2000],   # cap to avoid token overflow
        "raw_data": str(query_result)[:2000] if query_result else None,
        "sql_used": sql_used,
    })

    # Only return changed keys
    return {
        "current_step": current_step + 1,
        "tool_results": tool_results,
    }
