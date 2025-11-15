"""
State management for the LangGraph agent pipeline.
Defines the shared state structure passed between agents.
"""
from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime


class AgentState(TypedDict, total=False):  # ← TAMBAHKAN total=False
    """
    Shared state for the 4-agent pipeline: Planner -> Worker -> Critic -> Synthesizer.
    
    total=False allows optional fields and dynamic additions like llm_client, db_tools
    """
    # Input
    session_id: str
    user_id: str
    user_prompt: str
    
    # Context & Memory (injected by Memory Manager)
    context: str
    session_summary: Optional[str]
    last_k_turns: List[Dict[str, Any]]
    
    # Planner output
    subtasks: List[str]
    data_access_plan: str
    
    # Worker output
    worker_findings: List[Dict[str, Any]]
    tool_calls: List[Dict[str, Any]]
    
    # Critic output
    critic_passed: bool
    critic_feedback: str
    retry_count: int
    
    # Synthesizer output
    final_answer: str
    suggestions: List[str]
    
    # Metrics & Observability
    timings: Dict[str, float]
    request_start: float
    first_token_at: Optional[float]
    completed_at: Optional[float]
    
    # Streaming control
    stream_tokens: List[str]
    current_agent: str
    
    # Dependencies (injected by chat.py) - ADDED
    llm_client: Any  # LLMClient instance
    db_tools: Any    # DBTools instance
    memory_store: Any  # MemoryStore instance


def create_initial_state(
    session_id: str,
    user_id: str,
    user_prompt: str,
    context: str,
    session_summary: Optional[str] = None,
    last_k_turns: Optional[List[Dict[str, Any]]] = None
) -> AgentState:
    """
    Initialize state for a new turn.
    
    Args:
        session_id: Unique session identifier
        user_id: User identifier
        user_prompt: Current user message
        context: Packed context from Memory Manager
        session_summary: Long-term summary if exists
        last_k_turns: Short-term memory (last K turns)
    
    Returns:
        AgentState with initialized fields
    """
    now = datetime.utcnow().timestamp()
    
    return AgentState(
        # Input
        session_id=session_id,
        user_id=user_id,
        user_prompt=user_prompt,
        
        # Context
        context=context,
        session_summary=session_summary,
        last_k_turns=last_k_turns or [],
        
        # Planner (empty initially)
        subtasks=[],
        data_access_plan="",
        
        # Worker (empty initially)
        worker_findings=[],
        tool_calls=[],
        
        # Critic (empty initially)
        critic_passed=False,
        critic_feedback="",
        retry_count=0,
        
        # Synthesizer (empty initially)
        final_answer="",
        suggestions=[],
        
        # Metrics
        timings={},
        request_start=now,
        first_token_at=None,
        completed_at=None,
        
        # Streaming
        stream_tokens=[],
        current_agent=""
    )