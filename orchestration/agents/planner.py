"""
Planner Agent: Expands user prompt into subtasks and data access plan.
Must be context-aware using packed context from Memory Manager.
"""
from typing import Dict, Any
import time
import traceback

from ..state import AgentState


async def planner_node(state: AgentState) -> Dict[str, Any]:
    """
    Planner Agent: Expand user prompt into 1-3 subtasks and data access plan.
    """
    start_time = time.time()
    
    # Extract inputs
    user_prompt = state["user_prompt"]
    context = state["context"]
    llm_client = state.get("llm_client")
    
    subtasks = []
    data_plan = ""
    
    try:
        if not llm_client:
            raise ValueError("LLM client not found in state")
        
        # Build planning prompt
        planning_prompt = f"""You are a planning agent. Analyze the user's request considering conversation history.

{context}

Your task: Break down the current user request into 1-3 specific, actionable subtasks.
Also identify if any database queries are needed.

Format your response exactly like this:

SUBTASKS:
1. [First specific subtask]
2. [Second specific subtask]
3. [Third specific subtask if needed]

DATA_PLAN:
[Describe what data needs to be fetched, or write "No database access needed"]

Be specific and actionable. Each subtask should be clear.
"""
        
        print(f"[Planner] Calling LLM with context length: {len(context)}")
        response = await llm_client.generate(planning_prompt, max_tokens=300, temperature=0.5)
        print(f"[Planner] LLM response: {response[:200]}...")
        
        # Parse response
        lines = response.strip().split('\n')
        in_subtasks = False
        in_data_plan = False
        
        for line in lines:
            line = line.strip()
            
            if line.upper().startswith("SUBTASKS:"):
                in_subtasks = True
                in_data_plan = False
                continue
            elif line.upper().startswith("DATA_PLAN:") or line.upper().startswith("DATA PLAN:"):
                in_data_plan = True
                in_subtasks = False
                # Check if plan is on same line
                after_colon = line.split(':', 1)[1].strip() if ':' in line else ''
                if after_colon:
                    data_plan += after_colon + " "
                continue
            
            if in_subtasks and line:
                # Extract subtask
                if line[0].isdigit() or line.startswith('-') or line.startswith('•'):
                    task = line.split('.', 1)[-1].strip() if '.' in line else line.lstrip('0123456789.-•').strip()
                    if task and len(task) > 5:
                        subtasks.append(task)
            elif in_data_plan and line:
                data_plan += line + " "
        
        data_plan = data_plan.strip()
        
        # Fallback if parsing fails
        if not subtasks:
            print("[Planner] Parsing failed, using smart fallback")
            # Analyze if query needs history
            needs_history = any(word in user_prompt.lower() for word in [
                'my', 'our', 'previous', 'earlier', 'last', 'before', 
                'conversation', 'discussed', 'mentioned', 'said'
            ])
            
            if needs_history:
                subtasks = [
                    "Retrieve conversation history to understand context",
                    f"Analyze user's request: {user_prompt[:50]}",
                    "Formulate contextual response based on history"
                ]
                data_plan = "Query messages collection for session history"
            else:
                subtasks = [
                    f"Understand the request: {user_prompt[:50]}",
                    "Gather relevant information",
                    "Prepare comprehensive response"
                ]
                data_plan = "No database access needed for this request"
        
        if not data_plan:
            data_plan = "Determine data needs based on request context"
        
        print(f"[Planner] Generated {len(subtasks)} subtasks")
        print(f"[Planner] Data plan: {data_plan[:100]}")
        
    except Exception as e:
        print(f"[Planner] ERROR: {str(e)}")
        print(traceback.format_exc())
        
        # Critical fallback
        subtasks = [
            f"Process user request: {user_prompt[:60]}",
            "Gather necessary information",
            "Prepare appropriate response"
        ]
        data_plan = "Assess if database query needed during execution"
    
    # Calculate duration
    duration_ms = (time.time() - start_time) * 1000
    
    # Update state
    return {
        **state,
        "subtasks": subtasks,
        "data_access_plan": data_plan,
        "current_agent": "planner",
        "timings": {
            **state.get("timings", {}),
            "planner": duration_ms
        }
    }