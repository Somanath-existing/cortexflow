"""
Analytics Agent — Calls MCP Analytics server to generate charts and compute statistics.
Reads structured data from previous sql_agent tool_results and produces Plotly chart JSON.
"""
from langchain_core.messages import HumanMessage, SystemMessage
from backend.agents.state import AgentState
from backend.mcp.client import mcp_client
from backend.core.llm import get_llm
import json
import re

llm = get_llm("fast")

ANALYTICS_SYSTEM = """You are an analytics agent that generates charts and computes statistics.

You receive a task description and structured data from previous database queries stored in tool_results.
Your job is to:
1. Extract the relevant numeric data from tool_results
2. Choose the correct chart type:
   - "pie" → for proportions/share breakdown (e.g. revenue by category)
   - "bar" → for comparisons across categories or regions
   - "line" → for trends over time (quarters, years)
   - "scatter" → for correlation between two numeric variables
3. Format the data and parameters for the generate_chart tool

Output ONLY a valid JSON object with these fields:
{
  "chart_type": "pie|bar|line|scatter",
  "data": [{"field1": value, "field2": value}, ...],
  "x_field": "column_name_for_x_axis_or_labels",
  "y_field": "column_name_for_numeric_values",
  "title": "Chart Title",
  "color_field": "optional_column_for_color_grouping_or_null"
}

IMPORTANT: data must be a flat list of dicts. No nested objects. Numbers must be numeric, not strings."""


async def analytics_agent_node(state: AgentState) -> dict:
    current_step = state["current_step"]
    plan = state.get("plan", [])

    if current_step >= len(plan):
        return {"current_step": current_step + 1}

    task = plan[current_step]

    # Gather data from prior sql_agent tool_results
    prior_results = state.get("tool_results", [])
    prior_data_context = ""
    all_raw_data = []

    for r in prior_results:
        if r.get("agent") == "sql_agent" and r.get("raw_data"):
            try:
                parsed = json.loads(r["raw_data"])
                if isinstance(parsed, list) and len(parsed) > 0:
                    all_raw_data.extend(parsed)
                    prior_data_context += f"\nTask: {r['task']}\nData: {r['raw_data'][:800]}\n"
            except Exception:
                prior_data_context += f"\nTask: {r['task']}\nAnalysis: {r.get('analysis', '')[:400]}\n"

    if not prior_data_context:
        # Nothing to chart yet — skip
        tool_results = list(state.get("tool_results", []))
        tool_results.append({
            "step": current_step,
            "task": task,
            "agent": "analytics_agent",
            "analysis": "No structured data available from prior steps to generate a chart.",
            "raw_data": None,
            "sql_used": None,
        })
        return {
            "current_step": current_step + 1,
            "tool_results": tool_results,
        }

    # Ask LLM to decide chart params
    response = await llm.ainvoke([
        SystemMessage(content=ANALYTICS_SYSTEM),
        HumanMessage(content=f"""Task: {task}
Original question: {state['user_query']}

Available structured data from database queries:
{prior_data_context}

Output a JSON chart specification to visualize this data.""")
    ])

    # Strip <think> tags
    content = re.sub(r'<think>.*?</think>', '', response.content, flags=re.DOTALL).strip()

    # Extract JSON
    json_match = re.search(r'\{.*\}', content, re.DOTALL)
    chart_json_str = None
    analysis_text = "Chart generation attempted."

    if json_match:
        try:
            chart_spec = json.loads(json_match.group())

            # Validate required fields
            required = ["chart_type", "data", "x_field", "y_field", "title"]
            if all(k in chart_spec for k in required) and chart_spec["data"]:
                # Call Analytics MCP
                chart_result = await mcp_client.call_tool(
                    "analytics",
                    "generate_chart",
                    {
                        "chart_type": chart_spec["chart_type"],
                        "data": chart_spec["data"],
                        "x_field": chart_spec["x_field"],
                        "y_field": chart_spec["y_field"],
                        "title": chart_spec["title"],
                        "color_field": chart_spec.get("color_field"),
                    }
                )
                # chart_result is the raw Plotly JSON string
                if chart_result and not chart_result.startswith("Error"):
                    chart_json_str = chart_result
                    analysis_text = (
                        f"Generated {chart_spec['chart_type']} chart: '{chart_spec['title']}' "
                        f"with {len(chart_spec['data'])} data points."
                    )
                else:
                    analysis_text = f"Chart generation failed: {chart_result}"
            else:
                analysis_text = "LLM produced incomplete chart spec — missing required fields."
        except (json.JSONDecodeError, Exception) as e:
            analysis_text = f"Failed to parse chart specification: {str(e)}"
    else:
        analysis_text = "LLM did not produce a valid JSON chart specification."

    tool_results = list(state.get("tool_results", []))
    tool_results.append({
        "step": current_step,
        "task": task,
        "agent": "analytics_agent",
        "analysis": analysis_text,
        "raw_data": None,
        "sql_used": None,
    })

    result: dict = {
        "current_step": current_step + 1,
        "tool_results": tool_results,
    }

    # Only set chart_data if we actually got a chart
    if chart_json_str:
        result["chart_data"] = chart_json_str

    return result
