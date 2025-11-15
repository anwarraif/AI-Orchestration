"""
Session management endpoints.
Retrieve session info, history, and summaries.
"""
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List

from db.client import get_database
from db.models import SessionResponse, MessageDocument

router = APIRouter()


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get session details.
    
    Args:
        session_id: Session identifier
    
    Returns:
        SessionResponse with summary and metadata
    """
    session = await db["sessions"].find_one({"sessionId": session_id})
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Count messages
    message_count = await db["messages"].count_documents({"sessionId": session_id})
    
    return SessionResponse(
        sessionId=session["sessionId"],
        userId=session["userId"],
        summary=session.get("summary"),
        messageCount=message_count,
        createdAt=session["createdAt"],
        updatedAt=session["updatedAt"]
    )


@router.get("/{session_id}/messages", response_model=List[MessageDocument])
async def get_session_messages(
    session_id: str,
    limit: int = 50,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get session message history.
    
    Args:
        session_id: Session identifier
        limit: Maximum messages to return (default 50)
    
    Returns:
        List of messages ordered by timestamp
    """
    cursor = db["messages"].find(
        {"sessionId": session_id}
    ).sort("timestamp", 1).limit(limit)
    
    messages = await cursor.to_list(length=limit)
    
    return messages
