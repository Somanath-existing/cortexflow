from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langchain_core.messages import HumanMessage, AIMessage
from backend.agents.graph import cortexflow_graph
from backend.agents.state import AgentState
from backend.cache.redis_cache import (
    get_cached_response,
    set_cached_response,
    get_session_history,
    save_session_turn,
)
import uuid
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/{session_id}")
async def chat_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept()
    config = {"configurable": {"thread_id": session_id}}

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            # Check if this is a human-in-the-loop approval response
            if message.get("type") == "approval_response" or "action" in message:
                action = message.get("action", "")
                is_approved = action == "approve" or message.get("approved") is True

                await websocket.send_json({
                    "type": "status",
                    "message": f"🛡️ Received approval decision: {'Approved' if is_approved else 'Rejected'}. Resuming workflow..."
                })

                # Resume graph with approval outcome
                resume_state = {
                    "approval_granted": is_approved,
                    "needs_approval": False,
                }
                async for event in cortexflow_graph.astream(
                    resume_state,
                    config=config
                ):
                    for node_name, node_output in event.items():
                        await websocket.send_json({
                            "type": "agent_step",
                            "node": node_name,
                            "data": {
                                "plan": node_output.get("plan"),
                                "current_step": node_output.get("current_step"),
                                "tool_results_count": len(
                                    node_output.get("tool_results") or []
                                )
                            }
                        })

                final_state = await cortexflow_graph.aget_state(config)
                values = final_state.values

                await websocket.send_json({
                    "type": "final_answer",
                    "answer": values.get("final_answer", "Workflow completed."),
                    "sources": values.get("sources", []),
                    "chart_data": values.get("chart_data")
                })
                continue

            user_query = message.get("query", "")
            if not user_query.strip():
                continue

            # 1. High-speed Redis Cache Check (for exact repeated questions)
            cached_answer = await get_cached_response(user_query)
            if cached_answer and not message.get("force_refresh"):
                await websocket.send_json({
                    "type": "status",
                    "message": "⚡ Retrieved instant response from Redis cache"
                })
                await websocket.send_json({
                    "type": "final_answer",
                    "answer": cached_answer,
                    "sources": [{"agent": "redis_cache", "task": "Cached response hit", "type": "cache"}],
                    "chart_data": None
                })
                continue

            await websocket.send_json({
                "type": "status",
                "message": "🧠 Planning research strategy..."
            })

            # 2. Multi-turn memory: retrieve existing conversation messages
            existing_messages = []
            try:
                current_checkpoint = await cortexflow_graph.aget_state(config)
                if current_checkpoint and current_checkpoint.values.get("messages"):
                    existing_messages = list(current_checkpoint.values["messages"])
            except Exception:
                pass

            # Fallback to Redis session history if checkpointer was empty
            if not existing_messages:
                redis_history = await get_session_history(session_id)
                for turn in redis_history:
                    if turn.get("role") == "user":
                        existing_messages.append(HumanMessage(content=turn["content"]))
                    else:
                        existing_messages.append(AIMessage(content=turn["content"]))

            # Append current turn
            turn_messages = existing_messages + [HumanMessage(content=user_query)]

            initial_state: AgentState = {
                "messages": turn_messages,
                "user_query": user_query,
                "plan": [],
                "current_step": 0,
                "tool_results": [],
                "final_answer": "",
                "sources": [],
                "chart_data": None,
                "session_id": session_id,
                "needs_approval": False,
                "approval_prompt": None,
                "approval_granted": None,
                "error": None,
                "review_attempts": 0
            }

            # 3. Stream graph execution
            approval_halted = False
            async for event in cortexflow_graph.astream(
                initial_state,
                config=config
            ):
                for node_name, node_output in event.items():
                    await websocket.send_json({
                        "type": "agent_step",
                        "node": node_name,
                        "data": {
                            "plan": node_output.get("plan"),
                            "current_step": node_output.get("current_step"),
                            "tool_results_count": len(
                                node_output.get("tool_results") or []
                            )
                        }
                    })

                    # Check if human approval is required
                    if node_output.get("needs_approval"):
                        prompt = node_output.get("approval_prompt", "Human approval required to proceed.")
                        await websocket.send_json({
                            "type": "approval_required",
                            "prompt": prompt,
                            "step": node_output.get("current_step", 0)
                        })
                        approval_halted = True
                        break

                if approval_halted:
                    break

            if approval_halted:
                # Wait for user input in next loop iteration
                continue

            # 4. Get final state
            final_state = await cortexflow_graph.aget_state(config)
            values = final_state.values
            final_answer = values.get("final_answer", "No answer generated.")
            sources = values.get("sources", [])
            chart_data = values.get("chart_data")

            # 5. Persist to Redis Cache and Session History
            await set_cached_response(user_query, final_answer, ttl_seconds=3600)
            await save_session_turn(session_id, "user", user_query)
            await save_session_turn(session_id, "assistant", final_answer)

            await websocket.send_json({
                "type": "final_answer",
                "answer": final_answer,
                "sources": sources,
                "chart_data": chart_data
            })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"Agent error: {str(e)}"
            })
        except Exception:
            pass


@router.post("/query")
async def query_sync(request: dict):
    """Synchronous query endpoint for non-WebSocket clients."""
    user_query = request.get("query", "")
    session_id = request.get("session_id") or str(uuid.uuid4())

    # Check cache first
    cached_answer = await get_cached_response(user_query)
    if cached_answer and not request.get("force_refresh"):
        return {
            "answer": cached_answer,
            "sources": [{"agent": "redis_cache", "task": "Cached response hit", "type": "cache"}],
            "plan": [],
            "cached": True
        }

    initial_state: AgentState = {
        "messages": [HumanMessage(content=user_query)],
        "user_query": user_query,
        "plan": [],
        "current_step": 0,
        "tool_results": [],
        "final_answer": "",
        "sources": [],
        "chart_data": None,
        "session_id": session_id,
        "needs_approval": False,
        "approval_prompt": None,
        "approval_granted": None,
        "error": None,
        "review_attempts": 0
    }

    config = {"configurable": {"thread_id": session_id}}
    final = await cortexflow_graph.ainvoke(initial_state, config=config)

    answer = final.get("final_answer", "")
    await set_cached_response(user_query, answer, ttl_seconds=3600)
    await save_session_turn(session_id, "user", user_query)
    await save_session_turn(session_id, "assistant", answer)

    return {
        "answer": answer,
        "sources": final.get("sources", []),
        "plan": final.get("plan", []),
        "chart_data": final.get("chart_data")
    }
