from langchain_core.messages import HumanMessage, SystemMessage
from backend.agents.state import AgentState
from backend.core.llm import get_llm
import json
import re

llm = get_llm("reasoning")

RESPONDER_SYSTEM = """You are a business intelligence analyst presenting findings to a senior executive.

Based on the research conducted, provide:
1. A clear, direct answer to the question
2. Key evidence supporting your answer (cite specific data points and numbers)
3. Any important caveats or limitations
4. A recommended next action

Format your response using this structure:
**Answer:** [Direct, specific answer]

**Evidence:**
- [Key finding 1 with specific numbers]
- [Key finding 2 with specific numbers]

**Context:** [Important background or caveats]

**Recommendation:** [What to do next]

Be factual, cite exact numbers from the research, and be concise. Do not repeat yourself."""


async def responder_node(state: AgentState) -> dict:
    tool_results = state.get("tool_results", [])
    query = state["user_query"]

    if state.get("error"):
        return {
            "final_answer": f"I encountered an error processing your request: {state['error']}. Please try again.",
            "sources": [],
        }

    if not tool_results:
        return {
            "final_answer": "I was unable to gather sufficient data to answer your question. Please try rephrasing or check that the data services are running.",
            "sources": [],
        }

    # Build context — truncate each finding to avoid token overflow
    results_context = json.dumps([
        {
            "source": r["agent"],
            "task": r["task"],
            "findings": r["analysis"][:1000] if r.get("analysis") else "No findings",
            "sql_used": r.get("sql_used"),
            "raw_data": r["raw_data"][:500] if r.get("raw_data") else None,
        }
        for r in tool_results
    ], indent=2)

    response = await llm.ainvoke([
        SystemMessage(content=RESPONDER_SYSTEM),
        HumanMessage(content=f"""Question: {query}

Research findings:
{results_context}

Provide a comprehensive, well-structured answer using the evidence above.""")
    ])

    # Strip <think> tags from reasoning models
    final_answer = re.sub(r'<think>.*?</think>', '', response.content, flags=re.DOTALL).strip()

    sources = [
        {
            "agent": r["agent"],
            "task": r["task"],
            "type": (
                "database" if r["agent"] == "sql_agent"
                else "knowledge_graph" if r["agent"] == "graph_agent"
                else "analytics" if r["agent"] == "analytics_agent"
                else "approval" if r["agent"] == "approval_agent"
                else "document"
            ),
            "sql_used": r.get("sql_used"),
        }
        for r in tool_results
    ]

    result: dict = {
        "final_answer": final_answer,
        "sources": sources,
    }

    if state.get("chart_data"):
        result["chart_data"] = state["chart_data"]
    if state.get("needs_approval"):
        result["needs_approval"] = state["needs_approval"]
        result["approval_prompt"] = state.get("approval_prompt")

    return result
