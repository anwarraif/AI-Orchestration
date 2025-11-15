"""
Synthesizer Agent: Produces final text answer and 3 follow-up suggestions.
Final step in the pipeline before returning to user.
"""
from typing import Dict, Any
import time
import traceback

from ..state import AgentState


async def synthesizer_node(state: AgentState) -> Dict[str, Any]:
    """
    Synthesizer Agent: Generate final answer and 3 follow-up suggestions.
    """
    start_time = time.time()
    
    # Extract inputs
    user_prompt = state["user_prompt"]
    context = state["context"]
    worker_findings = state.get("worker_findings", [])
    critic_feedback = state.get("critic_feedback", "")
    critic_passed = state.get("critic_passed", True)
    llm_client = state.get("llm_client")
    
    final_answer = ""
    suggestions = []
    
    try:
        if not llm_client:
            raise ValueError("LLM client not found in state")
        
        # Build synthesis prompt
        findings_text = "\n".join([
            f"- {f.get('result', 'No result')}" 
            for f in worker_findings
        ]) if worker_findings else "No specific findings"
        
        synthesis_prompt = f"""You are a helpful AI assistant. Generate a natural, conversational response.

CONVERSATION CONTEXT:
{context}

ANALYSIS RESULTS:
{findings_text}

QUALITY CHECK: {critic_feedback}

Task: Provide a helpful, natural response to the user's request. If the conversation history contains relevant information (like the user's name, preferences, or previous topics), reference it appropriately.

Generate your response in this format:

ANSWER:
[Your natural, conversational response here - be specific and reference context when relevant]

SUGGESTIONS:
1. [Relevant follow-up question or action]
2. [Another relevant suggestion]
3. [Third suggestion]

Remember:
- Be conversational and natural
- Reference previous conversation context when relevant
- Keep the response focused and helpful
"""
        
        # Call LLM
        print(f"[Synthesizer] Calling LLM with prompt length: {len(synthesis_prompt)}")
        response = await llm_client.generate(synthesis_prompt, max_tokens=500, temperature=0.7)
        print(f"[Synthesizer] LLM response length: {len(response)}")
        
        # Parse response
        lines = response.strip().split('\n')
        in_answer = False
        in_suggestions = False
        answer_lines = []
        
        for line in lines:
            line = line.strip()
            
            if line.upper().startswith("ANSWER:"):
                in_answer = True
                in_suggestions = False
                # Check if answer is on same line
                after_colon = line.split(':', 1)[1].strip() if ':' in line else ''
                if after_colon:
                    answer_lines.append(after_colon)
                continue
            elif line.upper().startswith("SUGGESTIONS:"):
                in_suggestions = True
                in_answer = False
                continue
            
            if in_answer and line:
                answer_lines.append(line)
            elif in_suggestions and line:
                # Extract suggestion (handle numbered or bulleted)
                if line[0].isdigit() or line.startswith('-') or line.startswith('•'):
                    sug = line.split('.', 1)[-1].strip() if '.' in line else line.lstrip('0123456789.-•').strip()
                    if sug and len(sug) > 5:  # Valid suggestion
                        suggestions.append(sug)
        
        # Join answer lines
        final_answer = ' '.join(answer_lines).strip()
        
        # Fallback if parsing failed
        if not final_answer:
            print("[Synthesizer] Parsing failed, using fallback")
            # Try to use the full response if it looks reasonable
            if len(response) > 20 and not response.startswith("ANSWER:"):
                final_answer = response.strip()
            else:
                final_answer = f"I understand you're asking about: {user_prompt}. "
                if worker_findings and len(worker_findings) > 0:
                    final_answer += f"Based on my analysis: {worker_findings[0].get('result', '')}"
                else:
                    final_answer += "Let me help you with that."
        
        # Ensure we have 3 suggestions
        if len(suggestions) < 3:
            default_suggestions = [
                "Can you tell me more about this?",
                "What else would you like to know?",
                "Should we explore this topic further?"
            ]
            while len(suggestions) < 3:
                suggestions.append(default_suggestions[len(suggestions)])
        
        suggestions = suggestions[:3]  # Only keep 3
        
        print(f"[Synthesizer] Final answer length: {len(final_answer)}")
        print(f"[Synthesizer] Suggestions: {len(suggestions)}")
        
    except Exception as e:
        print(f"[Synthesizer] ERROR: {str(e)}")
        print(traceback.format_exc())
        
        # Critical fallback
        final_answer = f"I received your message: '{user_prompt}'. "
        if worker_findings:
            final_answer += f"Analysis shows: {worker_findings[0].get('result', 'completed successfully')}. "
        final_answer += "How can I help you further?"
        
        suggestions = [
            "Tell me more about what you need",
            "Can you clarify your question?",
            "What would you like to know next?"
        ]
    
    # Mark completion
    completed_at = time.time()
    duration_ms = (completed_at - start_time) * 1000
    
    # Update state
    return {
        **state,
        "final_answer": final_answer,
        "suggestions": suggestions,
        "completed_at": completed_at,
        "current_agent": "synthesizer",
        "timings": {
            **state.get("timings", {}),
            "synthesizer": duration_ms
        }
    }