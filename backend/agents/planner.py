from langchain_core.messages import HumanMessage, SystemMessage
from backend.agents.state import AgentState
from backend.core.llm import get_llm
import json
import re

llm = get_llm("reasoning")

PLANNER_SYSTEM = """You are a strategic planning agent for an enterprise data intelligence system.

Your job is to create a step-by-step plan to answer the user's business question.

Available capabilities (use EXACT prefixes):
- query_database: Run SQL queries against sales, customer, order, and customer_health tables
- search_documents: Search business reports, policies, market analyses, and guidelines
- find_in_graph: Traverse Neo4j knowledge graph for customer-product-region relationships and entity networks
- generate_chart: Generate Plotly charts (pie, bar, line, scatter) from query results (MUST include whenever user asks for a chart, visual, graph, plot, or pictorial representation)
- require_approval: Stop for human approval if the request requires sensitive action (e.g. customer escalation, discount approval, policy override)

Rules:
1. Break the question into 2-4 concrete research steps
2. When the user requests a chart or visualization, FIRST query_database to get the data, THEN generate_chart to visualize it
3. For entity connections, customer networks, or graph traversals, use find_in_graph
4. If the query asks to execute an escalation, grant a discount, or modify data, add a require_approval step
5. Consider the conversation history if this is a follow-up question

Output your plan as a JSON array of strings ONLY. No explanation, no markdown, just the raw array.
Examples:
User: "Generate a pie chart showing the revenue breakdown by product category in Kerala for Q3 2024"
Plan: ["query_database: Retrieve Q3 2024 revenue breakdown by product category for Kerala from regional_sales", "generate_chart: Create a pie chart of Kerala Q3 2024 revenue by product category"]

User: "What products did Kochi Tech Solutions purchase and what is their churn risk?"
Plan: ["find_in_graph: Find products and relationships for customer KOCHI001", "query_database: Retrieve customer health and churn risk for KOCHI001"]

User: "Escalate customer TVM001 and offer a 15% retention discount"
Plan: ["query_database: Check health score and order history for customer TVM001", "require_approval: Escalate customer TVM001 to retention team and offer 15% discount"]
"""


async def planner_node(state: AgentState) -> dict:
    query = state["user_query"]
    messages = state.get("messages", [])

    # Format recent conversation turns for context
    history_context = ""
    if messages:
        recent = messages[-6:]  # last 3 turns
        formatted_turns = []
        for m in recent:
            role = "User" if m.type in ("human", "user") else "Assistant"
            formatted_turns.append(f"{role}: {m.content[:300]}")
        if formatted_turns:
            history_context = "\nConversation History:\n" + "\n".join(formatted_turns) + "\n"

    prompt = f"{history_context}Current question: {query}\nCreate a research plan:"

    response = await llm.ainvoke([
        SystemMessage(content=PLANNER_SYSTEM),
        HumanMessage(content=prompt)
    ])

    content = response.content
    # Strip any <think>...</think> tags from reasoning models
    content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()

    json_match = re.search(r'\[.*?\]', content, re.DOTALL)

    if json_match:
        try:
            plan = json.loads(json_match.group())
        except json.JSONDecodeError:
            plan = [content.strip()]
    else:
        # Fallback plan
        if any(w in query.lower() for w in ["chart", "plot", "pie", "bar", "visual", "graph"]):
            plan = [
                f"query_database: Get data for: {query}",
                f"generate_chart: Visualize results for: {query}"
            ]
        elif any(w in query.lower() for w in ["graph", "relationship", "network", "connected"]):
            plan = [
                f"find_in_graph: Explore entities and connections for: {query}",
                f"query_database: Check database records for: {query}"
            ]
        else:
            plan = [
                f"query_database: Get relevant sales data for: {query}",
                f"search_documents: Find reports or policies related to: {query}",
            ]

    # Only return the keys we're modifying — never spread **state with Annotated fields
    return {
        "plan": plan,
        "current_step": 0,
        "tool_results": [],
        "error": None,
    }
