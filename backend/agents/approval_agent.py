"""
Approval Agent — Manages Human-in-the-Loop approvals for sensitive actions.
"""
from backend.agents.state import AgentState
import logging

logger = logging.getLogger(__name__)


async def approval_agent_node(state: AgentState) -> dict:
    current_step = state.get("current_step", 0)
    plan = state.get("plan", [])

    if current_step >= len(plan):
        return {"current_step": current_step + 1}

    task = plan[current_step]
    approval_granted = state.get("approval_granted")

    # If already decided by user
    if approval_granted is True:
        status_text = f"✅ Human Approval Granted: Proceeding with action '{task}'."
        needs_approval = False
    elif approval_granted is False:
        status_text = f"🛑 Human Approval Rejected: Action '{task}' was declined by user."
        needs_approval = False
    else:
        # Requires human decision
        action_desc = task.split(":", 1)[1].strip() if ":" in task else task
        prompt = f"Human approval required: Do you authorize '{action_desc}'?"
        status_text = f"⏸️ Awaiting human decision: {prompt}"
        needs_approval = True
        return {
            "needs_approval": True,
            "approval_prompt": prompt,
            "tool_results": list(state.get("tool_results", [])) + [{
                "step": current_step,
                "task": task,
                "agent": "approval_agent",
                "analysis": status_text,
                "raw_data": None,
                "sql_used": None,
            }],
        }

    tool_results = list(state.get("tool_results", []))
    tool_results.append({
        "step": current_step,
        "task": task,
        "agent": "approval_agent",
        "analysis": status_text,
        "raw_data": None,
        "sql_used": None,
    })

    return {
        "current_step": current_step + 1,
        "needs_approval": needs_approval,
        "tool_results": tool_results,
    }
