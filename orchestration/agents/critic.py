"""
Critic Agent: Validates Worker output and triggers retry if confidence is low.
Maximum 1 retry allowed (single recovery loop).
"""
from typing import Dict, Any
import time

from ..state import AgentState


async def critic_node(state: AgentState) -> Dict[str, Any]:
    """
    Critic Agent: Sanity-check Worker output and decide if retry is needed.
    
    Validation criteria:
    - Are findings complete?
    - Are tool calls successful?
    - Is data sufficient to answer user prompt?
    
    If confidence is low AND retry_count < 1, request retry.
    Otherwise, pass to Synthesizer.
    
    Args:
        state: Current agent state with worker_findings
    
    Returns:
        Updated state with critic_passed and critic_feedback
    """
    start_time = time.time()
    
    # Extract inputs
    worker_findings = state["worker_findings"]
    tool_calls = state.get("tool_calls", [])
    retry_count = state.get("retry_count", 0)
    user_prompt = state["user_prompt"]
    
    # Validation logic
    passed = True
    feedback = "Worker output validated successfully."
    
    # Check 1: Are there findings?
    if not worker_findings:
        passed = False
        feedback = "No findings returned by Worker."
    
    # Check 2: If tool calls made, were they successful?
    if tool_calls:
        failed_tools = [tc for tc in tool_calls if tc.get("result", {}).get("status") != "ok"]
        if failed_tools:
            passed = False
            feedback = f"Tool calls failed: {len(failed_tools)} failures detected."
    
    # Check 3: Does output seem relevant to user prompt?
    # (Simple heuristic: check if findings mention key terms from prompt)
    prompt_keywords = set(user_prompt.lower().split()[:5])  # First 5 words
    findings_text = " ".join([f.get("result", "") for f in worker_findings]).lower()
    relevance_score = sum(1 for kw in prompt_keywords if kw in findings_text)
    
    if relevance_score == 0:
        passed = False
        feedback = "Worker findings may not be relevant to user request."
    
    # Calculate duration
    duration_ms = (time.time() - start_time) * 1000
    
    # Update state
    new_retry_count = retry_count + 1 if not passed else retry_count
    
    return {
        **state,
        "critic_passed": passed,
        "critic_feedback": feedback,
        "retry_count": new_retry_count,
        "current_agent": "critic",
        "timings": {
            **state.get("timings", {}),
            "critic": duration_ms
        }
    }