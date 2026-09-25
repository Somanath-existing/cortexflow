from langchain_core.messages import HumanMessage, SystemMessage
from backend.agents.state import AgentState
from backend.mcp.client import mcp_client
from backend.core.llm import get_llm
import re

llm = get_llm("reasoning")

RESEARCHER_SYSTEM = """You are a research agent with access to enterprise documents and a knowledge graph.

When given a research task:
1. Review the document search results provided
2. Extract specific facts, numbers, and insights relevant to the question
3. Note any contradictions or gaps in the evidence
4. Synthesize findings into a clear, structured summary

Return your findings with specific quotes and data points. Be concise but complete."""


async def researcher_node(state: AgentState) -> dict:
    current_step = state["current_step"]
    plan = state.get("plan", [])

    if current_step >= len(plan):
        return {"current_step": current_step + 1}

    task = plan[current_step]

    # Call knowledge MCP for document search
    try:
        search_results = await mcp_client.call_tool(
            "knowledge",
            "search_documents",
            {"query": task, "top_k": 5}
        )
    except Exception as e:
        search_results = f"Document search unavailable: {str(e)}"

    # Also perform native PostgreSQL pgvector hybrid search
    try:
        from backend.rag.indexer import get_embedder
        from backend.db.postgres import search_pgvector
        embedder = get_embedder()
        q_emb = embedder.encode(task).tolist()
        pg_matches = await search_pgvector(q_emb, top_k=3)
        if pg_matches:
            pg_text = "\n\nAdditional PostgreSQL pgvector findings:\n" + "\n".join([
                f"- [Doc: {m.get('doc_id')}] {m.get('content', '')[:300]} (Score: {m.get('similarity')})"
                for m in pg_matches
            ])
            search_results = f"{search_results}{pg_text}"
    except Exception:
        pass  # Fall back to Qdrant if pgvector search fails

    response = await llm.ainvoke([
        SystemMessage(content=RESEARCHER_SYSTEM),
        HumanMessage(content=f"""Task: {task}
Original question: {state['user_query']}

Document search results:
{search_results}

Synthesize these findings. What do they tell us about the question?
Be specific with any numbers or facts found.""")
    ])

    # Strip <think> tags from reasoning models
    analysis = re.sub(r'<think>.*?</think>', '', response.content, flags=re.DOTALL).strip()

    tool_results = list(state.get("tool_results", []))
    tool_results.append({
        "step": current_step,
        "task": task,
        "agent": "researcher",
        "analysis": analysis,
        "raw_data": search_results,
        "sql_used": None,
    })

    # Only return changed keys
    return {
        "current_step": current_step + 1,
        "tool_results": tool_results,
    }
