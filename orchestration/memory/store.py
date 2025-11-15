"""
MongoDB-backed memory store for conversation history and summaries.
Handles persistence of messages, sessions, and long-term summaries.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..tools.time import utc_now, format_iso


class MemoryStore:
    """
    Persistent memory storage using MongoDB.
    
    Collections:
    - messages: Individual conversation turns
    - sessions: Session metadata and summaries
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize memory store.
        
        Args:
            db: MongoDB database instance
        """
        self.db = db
        self.messages_collection = db["messages"]
        self.sessions_collection = db["sessions"]
    
    async def save_message(
        self,
        session_id: str,
        user_id: str,
        role: str,  # "user" or "assistant"
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Save a conversation message.
        
        Args:
            session_id: Session identifier
            user_id: User identifier
            role: Message role ("user" or "assistant")
            content: Message content
            metadata: Optional metadata (timings, suggestions, etc.)
        
        Returns:
            str: Inserted message ID
        """
        message = {
            "sessionId": session_id,
            "userId": user_id,
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "createdAt": format_iso(),
            "timestamp": utc_now().timestamp()
        }
        
        result = await self.messages_collection.insert_one(message)
        return str(result.inserted_id)
    
    async def get_session_messages(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve messages for a session, ordered by timestamp.
        
        Args:
            session_id: Session identifier
            limit: Optional limit (most recent N messages)
        
        Returns:
            List of message documents
        """
        query = {"sessionId": session_id}
        cursor = self.messages_collection.find(query).sort("timestamp", 1)
        
        if limit:
            # Get last N messages
            total_count = await self.messages_collection.count_documents(query)
            skip = max(0, total_count - limit)
            cursor = cursor.skip(skip).limit(limit)
        
        messages = await cursor.to_list(length=None)
        return messages
    
    async def get_session_summary(self, session_id: str) -> Optional[str]:
        """
        Retrieve long-term summary for a session.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Summary text or None if not exists
        """
        session = await self.sessions_collection.find_one({"sessionId": session_id})
        if session:
            return session.get("summary")
        return None
    
    async def update_session_summary(
        self,
        session_id: str,
        summary: str,
        user_id: str
    ):
        """
        Update or create session summary.
        
        Args:
            session_id: Session identifier
            summary: New summary text
            user_id: User identifier
        """
        await self.sessions_collection.update_one(
            {"sessionId": session_id},
            {
                "$set": {
                    "summary": summary,
                    "userId": user_id,
                    "updatedAt": format_iso()
                },
                "$setOnInsert": {
                    "createdAt": format_iso()
                }
            },
            upsert=True
        )
    
    async def get_or_create_session(
        self,
        session_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get existing session or create new one.
        
        Args:
            session_id: Session identifier
            user_id: User identifier
        
        Returns:
            Session document
        """
        session = await self.sessions_collection.find_one({"sessionId": session_id})
        
        if not session:
            session = {
                "sessionId": session_id,
                "userId": user_id,
                "summary": None,
                "createdAt": format_iso(),
                "updatedAt": format_iso()
            }
            await self.sessions_collection.insert_one(session)
        
        return session
    
    async def count_session_messages(self, session_id: str) -> int:
        """
        Count total messages in a session.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Message count
        """
        return await self.messages_collection.count_documents({"sessionId": session_id})
