from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from backend.agents.state import AgentState
from backend.agents.planner import planner_node
from backend.agents.researcher import researcher_node
from backend.agents.sql_agent import sql_agent_node
from backend.agents.graph_agent import graph_agent_node
from backend.agents.analytics_agent import analytics_agent_node
from backend.agents.approval_agent import approval_agent_node
from backend.agents.critic import critic_node
from backend.agents.responder import responder_node


def should_continue(state: AgentState) -> str:
    """Router — decides what to do after each plan step."""

    # Error occurred — go straight to responder
    if state.get("error"):
        return "responder"

    current = state.get("current_step", 0)
    plan = state.get("plan", [])

    # All plan steps done — hand off to critic
    if current >= len(plan):
        return "critic"

    step_text = plan[current].strip().lower()

    # 1. Human Approval Check
    if (
        step_text.startswith("require_approval:")
        or any(w in step_text for w in ["escalate", "discount", "override", "approval"])
    ):
        return "approval_agent"

    # 2. Knowledge Graph Check (prioritized over generic keywords like 'customer')
    if (
        step_text.startswith("find_in_graph:")
        or step_text.startswith("graph:")
        or any(w in step_text for w in ["in_graph", "knowledge graph", "neo4j", "relationships", "entity network", "connected to"])
    ):
        return "graph_agent"

    # 3. Analytics & Charting Check
    if (
        step_text.startswith("generate_chart:")
        or step_text.startswith("calculate_analytics:")
        or step_text.startswith("chart:")
        or any(w in step_text for w in ["generate_chart", "plotly", "visualize", "visualization", "pie chart", "bar chart", "line chart", "scatter chart"])
    ):
        return "analytics_agent"

    # 4. Database Query Check
    if (
        step_text.startswith("query_database:")
        or step_text.startswith("sql:")
        or any(w in step_text for w in ["query", "database", "sql", "table", "sales", "revenue", "orders", "churn"])
    ):
        return "sql_agent"

    # 5. Semantic Document Search Check
    if (
        step_text.startswith("search_documents:")
        or step_text.startswith("search:")
        or any(w in step_text for w in ["search", "document", "documents", "policy", "report", "guideline", "market"])
    ):
        return "researcher"

    # Fallback default
    return "sql_agent" if "customer" in step_text else "researcher"


def critic_router(state: AgentState) -> str:
    """After critic review — finalize or replan."""
    messages = state.get("messages", [])

    if not messages:
        return "responder"

    last_message = messages[-1].content
    review_attempts = state.get("review_attempts", 0)

    if (
        review_attempts < 2
        and ("INSUFFICIENT" in last_message or "REPLAN" in last_message)
    ):
        return "planner"
    return "responder"


def build_graph():
    workflow = StateGraph(AgentState)

    # Add all agent nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("sql_agent", sql_agent_node)
    workflow.add_node("graph_agent", graph_agent_node)
    workflow.add_node("analytics_agent", analytics_agent_node)
    workflow.add_node("approval_agent", approval_agent_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("responder", responder_node)

    # Entry point
    workflow.set_entry_point("planner")

    route_map = {
        "sql_agent": "sql_agent",
        "researcher": "researcher",
        "graph_agent": "graph_agent",
        "analytics_agent": "analytics_agent",
        "approval_agent": "approval_agent",
        "critic": "critic",
        "responder": "responder",
    }

    # Conditional routing after planner
    workflow.add_conditional_edges("planner", should_continue, route_map)

    # After each worker agent — check if more steps needed
    for node in ["researcher", "sql_agent", "graph_agent", "analytics_agent", "approval_agent"]:
        workflow.add_conditional_edges(node, should_continue, route_map)

    # After critic — re-plan or finalize
    workflow.add_conditional_edges(
        "critic",
        critic_router,
        {
            "planner": "planner",
            "responder": "responder",
        },
    )

    # Responder always ends
    workflow.add_edge("responder", END)

    # MemorySaver checkpointer required for aget_state()
    checkpointer = MemorySaver()
    return workflow.compile(checkpointer=checkpointer)


# Singleton — built once at module load
cortexflow_graph = build_graph()
