"""
Graph Agent — Traverses the Neo4j knowledge graph to find entity relationships.
Used for questions about customer-product-region relationships.
"""
from langchain_core.messages import HumanMessage, SystemMessage
from backend.agents.state import AgentState
from backend.rag.graph_rag import graph_rag
from backend.core.llm import get_llm
import re
import json

llm = get_llm("reasoning")

GRAPH_SYSTEM = """You are a knowledge graph analyst with access to a Neo4j graph database.

The graph contains:
- Customer nodes (id, name, region, segment)
- Product nodes (id, name, category, unit_price)
- Region nodes (name, zone, country)
- Relationships: (:Customer)-[:PURCHASED]->(:Product), (:Customer)-[:LOCATED_IN]->(:Region)

When given graph query results, extract meaningful insights about:
- Which customers are connected to which products/regions
- Purchase patterns and relationship strengths
- Geographic clustering of customers

Be specific: mention entity names, relationship types, and counts.
Keep your analysis under 400 words."""


async def graph_agent_node(state: AgentState) -> dict:
    current_step = state["current_step"]
    plan = state.get("plan", [])

    if current_step >= len(plan):
        return {"current_step": current_step + 1}

    task = plan[current_step]
    query = state["user_query"]

    # Extract entity hints from the task
    task_lower = task.lower()
    graph_data = {}

    try:
        # Check what kind of graph query is needed
        if any(w in task_lower for w in ["kerala", "karnataka", "region", "south india"]):
            # Regional revenue graph
            region = None
            if "kerala" in task_lower:
                region = "Kerala"
            elif "karnataka" in task_lower:
                region = "Karnataka"
            graph_data = await graph_rag.get_revenue_graph(region=region)

        elif any(w in task_lower for w in ["customer", "kochi", "trivandrum", "bangalore", "calicut"]):
            # Customer relationship lookup
            customer_map = {
                "kochi": "KOCHI001",
                "trivandrum": "TVM001",
                "calicut": "CLT001",
                "bangalore": "BLR001",
                "mysore": "MYS001",
                "chennai": "CHN001",
                "hyderabad": "HYD001",
            }
            customer_id = None
            for name, cid in customer_map.items():
                if name in task_lower:
                    customer_id = cid
                    break

            if customer_id:
                records = await graph_rag.find_customer_relationships(customer_id)
                graph_data = {"customer_relationships": records}
            else:
                # Generic entity search — extract key entity from task
                words = [w for w in task.split() if len(w) > 4 and w[0].isupper()]
                entity = words[0] if words else "Kerala"
                records = await graph_rag.find_related_entities(entity, depth=2)
                graph_data = {"related_entities": records}

        else:
            # Fallback: full South India graph
            graph_data = await graph_rag.get_revenue_graph(region=None)

    except Exception as e:
        graph_data = {"error": str(e)}

    graph_str = json.dumps(graph_data, indent=2, default=str)[:1500]

    response = await llm.ainvoke([
        SystemMessage(content=GRAPH_SYSTEM),
        HumanMessage(content=f"""Task: {task}
Original question: {query}

Neo4j Knowledge Graph Results:
{graph_str}

What do these entity relationships tell us about the question?""")
    ])

    # Strip <think> tags
    analysis = re.sub(r'<think>.*?</think>', '', response.content, flags=re.DOTALL).strip()

    tool_results = list(state.get("tool_results", []))
    tool_results.append({
        "step": current_step,
        "task": task,
        "agent": "graph_agent",
        "analysis": analysis[:600],
        "raw_data": graph_str[:500],
        "sql_used": None,
    })

    return {
        "current_step": current_step + 1,
        "tool_results": tool_results,
    }
