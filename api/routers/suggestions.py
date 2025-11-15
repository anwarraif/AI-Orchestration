"""
Suggestions retrieval endpoints.
Get follow-up suggestions for messages or sessions.
"""
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List

from db.client import get_database
from db.models import SuggestionResponse

router = APIRouter()


@router.get("/{message_id}", response_model=SuggestionResponse)
async def get_message_suggestions(
    message_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get suggestions for a specific message.
    
    Args:
        message_id: Message identifier
    
    Returns:
        SuggestionResponse with 3 suggestions
    """
    suggestion = await db["suggestions"].find_one({"messageId": message_id})
    
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestions not found")
    
    return SuggestionResponse(
        messageId=suggestion["messageId"],
        suggestions=suggestion["suggestions"],
        createdAt=suggestion["createdAt"]
    )


@router.get("/session/{session_id}", response_model=List[SuggestionResponse])
async def get_session_suggestions(
    session_id: str,
    limit: int = 10,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get all suggestions for a session.
    
    Args:
        session_id: Session identifier
        limit: Maximum suggestions to return (default 10)
    
    Returns:
        List of suggestion responses
    """
    cursor = db["suggestions"].find(
        {"sessionId": session_id}
    ).sort("createdAt", -1).limit(limit)
    
    suggestions = await cursor.to_list(length=limit)
    
    return [
        SuggestionResponse(
            messageId=s["messageId"],
            suggestions=s["suggestions"],
            createdAt=s["createdAt"]
        )
        for s in suggestions
    ]
