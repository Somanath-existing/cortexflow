from typing import TypedDict, Annotated, Sequence, Optional, Any
from langchain_core.messages import BaseMessage
import operator


class AgentState(TypedDict):
    # The conversation
    messages: Annotated[Sequence[BaseMessage], operator.add]

    # Current query from user
    user_query: str

    # Plan created by planner
    plan: list[str]

    # Current step being executed
    current_step: int

    # All tool results collected
    tool_results: list[dict]

    # Final answer
    final_answer: str

    # Source citations
    sources: list[dict]

    # Chart data if applicable
    chart_data: Optional[Any]

    # Session ID
    session_id: str

    # Whether human approval is needed
    needs_approval: bool

    # Human-in-the-loop approval details
    approval_prompt: Optional[str]
    approval_granted: Optional[bool]

    # Error state
    error: Optional[str]

    # Number of critic reviews used by the workflow
    review_attempts: int
