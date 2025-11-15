"""
Chat streaming endpoint - core SSE streaming functionality.
Orchestrates the 4-agent pipeline and streams responses.
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional, AsyncIterator
import json
import asyncio
import time

from db.client import get_database
from db.models import ChatRequest, ChatResponse
from orchestration.state import create_initial_state
from orchestration.graph import create_agent_graph
from orchestration.memory.store import MemoryStore
from orchestration.memory.context_manager import ContextManager
from orchestration.tools.db_tools import DBTools
from orchestration.tools.time import format_iso, calculate_ttft, calculate_total_time
from orchestration.llm.provider import create_llm_client

router = APIRouter()


def verify_auth(
    authorization: Optional[str] = Header(None),
    token: Optional[str] = None  # ← Accept from query param
):
    """
    Simple auth verification with fallback to query param.
    
    Args:
        authorization: Bearer token from header
        token: Token from query parameter (fallback)
    
    Raises:
        HTTPException: If unauthorized
    """
    expected_token = "devkey"
    
    # Try header first
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            if parts[1] == expected_token:
                return  # Valid
    
    # Fallback to query param
    if token == expected_token:
        return  # Valid
    
    # Neither worked
    if not authorization and not token:
        raise HTTPException(status_code=401, detail="Missing authorization header or token parameter")
    else:
        raise HTTPException(status_code=401, detail="Invalid token")


async def stream_chat_response(
    request: ChatRequest,
    db: AsyncIOMotorDatabase
) -> AsyncIterator[str]:
    """
    Generate SSE stream for chat response.
    
    SSE Event types:
    - agent: Agent switch notification
    - tool_call_started: DB tool invocation started
    - tool_call_completed: DB tool completed
    - token: Streaming text token
    - done: Final response with metadata
    
    Args:
        request: Chat request with sessionId, userId, prompt
        db: Database instance
    
    Yields:
        SSE formatted events
    """
    try:
        # Initialize components
        memory_store = MemoryStore(db)
        context_manager = ContextManager(memory_store)
        db_tools = DBTools(db)
        llm_client = create_llm_client()
        
        # Get or create session
        await memory_store.get_or_create_session(request.sessionId, request.userId)
        
        # Pack context
        context_data = await context_manager.pack_context(
            request.sessionId,
            request.userId,
            request.prompt
        )
        
        # Create initial state
        state = create_initial_state(
            session_id=request.sessionId,
            user_id=request.userId,
            user_prompt=request.prompt,
            context=context_data["context"],
            session_summary=context_data.get("summary"),
            last_k_turns=context_data.get("last_k_turns", [])
        )
        state["memory_store"] = memory_store
        state["db_tools"] = db_tools
        state["llm_client"] = llm_client
        
        # Save user message
        await memory_store.save_message(
            session_id=request.sessionId,
            user_id=request.userId,
            role="user",
            content=request.prompt
        )
        
        # Create agent graph
        graph = create_agent_graph()
        
        # Track first token
        first_token_sent = False
        
        # Execute graph with streaming
        async for event in graph.astream(state):
            node_name = list(event.keys())[0]
            updated_state = event[node_name]
            
            # Emit agent event
            yield f"event: agent\n"
            yield f"data: {json.dumps({'name': node_name})}\n\n"
            
            # If worker node, emit tool call events
            if node_name == "worker" and updated_state.get("tool_calls"):
                for tool_call in updated_state["tool_calls"]:
                    # Tool call started
                    yield "event: tool_call_started\n"
                    data_started = {
                        "tool": tool_call["tool"],
                        "args": tool_call["args"]
                    }
                    yield f"data: {json.dumps(data_started)}\n\n"

                    
                    # Tool call completed
                    yield "event: tool_call_completed\n"
                    data_completed = {
                        "tool": tool_call["tool"],
                        "ok": tool_call["result"]["status"] == "ok",
                        "latencyMs": tool_call["latency_ms"]
                    }
                    yield f"data: {json.dumps(data_completed)}\n\n"

            
            # If synthesizer node, stream tokens
            if node_name == "synthesizer":
                final_answer = updated_state.get("final_answer", "")
                
                # Stream tokens (split by words for demo)
                words = final_answer.split()
                for word in words:
                    # Mark first token time
                    if not first_token_sent:
                        updated_state["first_token_at"] = time.time()
                        first_token_sent = True
                    
                    yield f"event: token\n"
                    yield f"data: {json.dumps({'text': word + ' '})}\n\n"
                    await asyncio.sleep(0.05)  # Simulate streaming delay
            
            # Update state
            state = updated_state
        
        # Calculate metrics
        ttft = calculate_ttft(state["request_start"], state.get("first_token_at"))
        total_time = calculate_total_time(state["request_start"], state.get("completed_at"))
        
        # Save assistant message
        message_id = await memory_store.save_message(
            session_id=request.sessionId,
            user_id=request.userId,
            role="assistant",
            content=state["final_answer"],
            metadata={
                "suggestions": state["suggestions"],
                "timings": state["timings"],
                "ttft_ms": ttft,
                "total_time_ms": total_time
            }
        )
        
        # Save suggestions
        await db["suggestions"].insert_one({
            "sessionId": request.sessionId,
            "userId": request.userId,
            "messageId": message_id,
            "suggestions": state["suggestions"],
            "createdAt": format_iso()
        })
        
        # Save metrics
        await db["metrics"].insert_one({
            "sessionId": request.sessionId,
            "userId": request.userId,
            "messageId": message_id,
            "ttft_ms": ttft,
            "total_time_ms": total_time,
            "tool_call_count": len(state.get("tool_calls", [])),
            "agent_timings": state.get("timings", {}),
            "timestamp": format_iso()
        })
        
        # Save tool calls
        for tool_call in state.get("tool_calls", []):
            await db["tool_calls"].insert_one({
                "sessionId": request.sessionId,
                "userId": request.userId,
                **tool_call
            })
        
        # Emit done event
        done_data = {
            "fullText": state["final_answer"],
            "suggestions": state["suggestions"],
            "timings": {
                "requestStart": state["request_start"],
                "firstTokenAt": state.get("first_token_at"),
                "completedAt": state.get("completed_at"),
                "ttft_ms": ttft,
                "total_ms": total_time
            }
        }
        
        yield f"event: done\n"
        yield f"data: {json.dumps(done_data)}\n\n"
        
    except Exception as e:
        # Emit error event
        yield f"event: error\n"
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


@router.post("/stream")
async def stream_chat(
    request: ChatRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    _auth: None = Depends(verify_auth)
):
    """
    Stream chat response via SSE.
    
    Request body:
        {
            "sessionId": "session_123",
            "userId": "user_abc",
            "prompt": "Your question here"
        }
    
    SSE Events:
        - agent: {"name": "planner|worker|critic|synthesizer"}
        - tool_call_started: {"tool": "db.find", "args": {...}}
        - tool_call_completed: {"tool": "db.find", "ok": true, "latencyMs": 7.5}
        - token: {"text": "word "}
        - done: {"fullText": "...", "suggestions": [...], "timings": {...}}
    
    Returns:
        StreamingResponse with text/event-stream content type
    """
    return StreamingResponse(
        stream_chat_response(request, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
