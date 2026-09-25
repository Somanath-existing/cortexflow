from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from backend.agents.state import AgentState
from backend.core.llm import get_llm
import json
import re

llm = get_llm("reasoning")

CRITIC_SYSTEM = """You are a critical review agent. Evaluate whether the research conducted is sufficient to answer the user's question accurately.

Evaluate across 4 dimensions:
1. COMPLETENESS: Does the evidence cover all aspects of the question?
2. ACCURACY: Is the data from reliable sources (database queries, documents)?
3. CONSISTENCY: Do different sources agree or contradict each other?
4. SUFFICIENCY: Is there enough evidence to give a confident answer?

Respond with ONE of:
- SUFFICIENT — if research is complete and accurate
- INSUFFICIENT - [specific gap] — if a specific piece of data is missing
- REPLAN - [what to add] — if the research plan needs a new direction

Be decisive. Default to SUFFICIENT if research has any data points relevant to the question."""


async def critic_node(state: AgentState) -> dict:
    tool_results = state.get("tool_results", [])
    query = state["user_query"]

    # Truncate analysis to prevent token explosion
    results_summary = json.dumps([
        {
            "task": r["task"],
            "agent": r["agent"],
            "findings": r["analysis"][:600] if r.get("analysis") else "No findings"
        }
        for r in tool_results
    ], indent=2)

    response = await llm.ainvoke([
        SystemMessage(content=CRITIC_SYSTEM),
        HumanMessage(content=f"""Original question: {query}

Research conducted:
{results_summary}

Is this research sufficient to answer the question?""")
    ])

    # Strip <think> tags
    verdict = re.sub(r'<think>.*?</think>', '', response.content, flags=re.DOTALL).strip()

    # Only return changed keys — messages uses Annotated reducer so we append via list
    return {
        "messages": [AIMessage(content=verdict)],
        "review_attempts": state.get("review_attempts", 0) + 1,
    }
