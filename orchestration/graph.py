"""
LangGraph orchestration for the 4-agent pipeline.
Defines the graph structure and execution flow.
"""
from langgraph.graph import StateGraph, END
from typing import Dict, Any
import time

from .state import AgentState
from .agents.planner import planner_node
from .agents.worker import worker_node
from .agents.critic import critic_node
from .agents.synthesizer import synthesizer_node


def should_retry(state: AgentState) -> str:
    """
    Conditional edge: decide if Worker should retry based on Critic feedback.
    
    Args:
        state: Current agent state
    
    Returns:
        "worker" if retry needed (retry_count < 1), else "synthesizer"
    """
    if not state["critic_passed"] and state["retry_count"] < 1:
        return "worker"
    return "synthesizer"


def create_agent_graph() -> StateGraph:
    """
    Create the LangGraph pipeline:
    
    Planner → Worker → Critic → (retry?) → Synthesizer → END
    
    Flow:
    1. Planner receives packed context and expands prompt into subtasks
    2. Worker executes subtasks and calls DB tools
    3. Critic validates output; if confidence low, retry once
    4. Synthesizer produces final answer + 3 suggestions
    
    Returns:
        Compiled LangGraph StateGraph
    """
    # Initialize graph
    workflow = StateGraph(AgentState)
    
    # Add nodes (agents)
    workflow.add_node("planner", planner_node)
    workflow.add_node("worker", worker_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("synthesizer", synthesizer_node)
    
    # Define edges (flow)
    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "worker")
    workflow.add_edge("worker", "critic")
    
    # Conditional edge: retry logic
    workflow.add_conditional_edges(
        "critic",
        should_retry,
        {
            "worker": "worker",  # Retry Worker (max 1 time)
            "synthesizer": "synthesizer"  # Move to Synthesizer
        }
    )
    
    workflow.add_edge("synthesizer", END)
    
    # Compile graph
    return workflow.compile()


async def run_agent_graph(
    state: AgentState,
    stream_callback=None
) -> AgentState:
    """
    Execute the agent graph with optional streaming callback.
    
    Args:
        state: Initial agent state
        stream_callback: Optional async callback for SSE events
            Signature: async def callback(event_type: str, data: dict)
    
    Returns:
        Final state after all agents executed
    """
    graph = create_agent_graph()
    
    # Execute graph
    async for event in graph.astream(state):
        # event is a dict: {node_name: updated_state}
        node_name = list(event.keys())[0]
        updated_state = event[node_name]
        
        # Emit SSE event for agent switch
        if stream_callback:
            await stream_callback("agent", {"name": node_name})
        
        # Update state reference
        state = updated_state
    
    return state