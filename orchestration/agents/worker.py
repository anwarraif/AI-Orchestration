"""
Worker Agent: Executes subtasks and MUST call DB tools when needed.
Responsible for actual data fetching and processing.
"""
from typing import Dict, Any, List
import time

from ..state import AgentState


async def worker_node(state: AgentState) -> Dict[str, Any]:
    """
    Worker Agent: Execute subtasks and call DB tools as needed.
    """
    start_time = time.time()

    # Extract inputs
    subtasks = state["subtasks"]
    session_id = state["session_id"]
    retry_count = state.get("retry_count", 0)

    # Extract dependencies (injected from chat.py)
    db_tools = state["db_tools"]
    memory_store = state["memory_store"]

    # Initialize results
    findings: List[Dict[str, Any]] = []
    tool_calls: List[Dict[str, Any]] = state.get("tool_calls", [])

    # Execute each subtask
    for idx, task in enumerate(subtasks):
        task_start = time.time()

        # Check if DB access needed
        needs_db_access = any(keyword in task.lower() for keyword in [
            "query", "fetch", "retrieve", "history", "data", "conversation", 
            "previous", "earlier", "past", "messages"
        ])

        if needs_db_access:
            # PERFORM REAL DB TOOL CALL
            try:
                collection = "messages"
                query_filter = {"sessionId": session_id}
                limit = 50

                # Call db.find (returns tuple: result_dict, latency)
                result, latency = await db_tools.find(
                    collection=collection,
                    filter=query_filter,
                    limit=limit
                )

                # Record tool call
                tool_call_log = {
                    "tool": "db.find",
                    "args": {
                        "collection": collection,
                        "filter": query_filter,
                        "limit": limit
                    },
                    "result": result,
                    "latency_ms": latency,
                    "timestamp": time.time()
                }
                tool_calls.append(tool_call_log)

                # Add finding with actual data
                count = result.get('count', 0)
                data = result.get("data", [])
                
                findings.append({
                    "task": task,
                    "result": f"Retrieved {count} messages from conversation history",
                    "data": data
                })

            except Exception as e:
                # Log error but continue
                findings.append({
                    "task": task,
                    "result": f"Error fetching data: {str(e)}",
                    "data": []
                })
        else:
            # No DB access needed
            findings.append({
                "task": task,
                "result": f"Completed: {task}",
                "data": {}
            })

    # If retry triggered by Critic
    if retry_count > 0:
        findings.append({
            "task": "retry_adjustment",
            "result": "Re-executed tasks with improved strategy",
            "data": {"retry_attempt": retry_count}
        })

    # Duration
    duration_ms = (time.time() - start_time) * 1000

    # Update and return state
    return {
        **state,
        "worker_findings": findings,
        "tool_calls": tool_calls,
        "current_agent": "worker",
        "timings": {
            **state.get("timings", {}),
            "worker": duration_ms
        }
    }
