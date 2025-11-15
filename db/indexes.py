"""
MongoDB index definitions for optimal query performance.
Creates indexes on frequently queried fields.
"""
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging

logger = logging.getLogger(__name__)


async def create_indexes(db: AsyncIOMotorDatabase):
    """
    Create all required indexes for the application.
    
    Indexes improve query performance for:
    - Session-based message retrieval
    - User activity queries
    - Time-based sorting and filtering
    - Tool call analytics
    
    Args:
        db: MongoDB database instance
    """
    logger.info("Creating MongoDB indexes...")
    
    try:
        # ====================================================================
        # Messages Collection Indexes
        # ====================================================================
        messages = db["messages"]
        
        # Compound index: sessionId + timestamp (for retrieving session history)
        await messages.create_index(
            [("sessionId", 1), ("timestamp", 1)],
            name="idx_session_timestamp"
        )
        
        # Index: userId (for user activity queries)
        await messages.create_index(
            [("userId", 1)],
            name="idx_user"
        )
        
        # Index: createdAt (for time-based queries)
        await messages.create_index(
            [("createdAt", -1)],
            name="idx_created_at"
        )
        
        # Compound index: userId + sessionId (for user session queries)
        await messages.create_index(
            [("userId", 1), ("sessionId", 1)],
            name="idx_user_session"
        )
        
        logger.info("✓ Messages indexes created")
        
        # ====================================================================
        # Sessions Collection Indexes
        # ====================================================================
        sessions = db["sessions"]
        
        # Unique index: sessionId
        await sessions.create_index(
            [("sessionId", 1)],
            name="idx_session_id",
            unique=True
        )
        
        # Index: userId (for retrieving all user sessions)
        await sessions.create_index(
            [("userId", 1)],
            name="idx_user"
        )
        
        # Index: updatedAt (for recent activity)
        await sessions.create_index(
            [("updatedAt", -1)],
            name="idx_updated_at"
        )
        
        logger.info("✓ Sessions indexes created")
        
        # ====================================================================
        # Tool Calls Collection Indexes
        # ====================================================================
        tool_calls = db["tool_calls"]
        
        # Compound index: sessionId + timestamp (for session analytics)
        await tool_calls.create_index(
            [("sessionId", 1), ("timestamp", -1)],
            name="idx_session_timestamp"
        )
        
        # Index: userId (for user tool usage analytics)
        await tool_calls.create_index(
            [("userId", 1)],
            name="idx_user"
        )
        
        # Index: tool (for tool-specific analytics)
        await tool_calls.create_index(
            [("tool", 1)],
            name="idx_tool"
        )
        
        # Index: timestamp (for time-based queries)
        await tool_calls.create_index(
            [("timestamp", -1)],
            name="idx_timestamp"
        )
        
        # Compound index: tool + result.status (for success/failure analytics)
        await tool_calls.create_index(
            [("tool", 1), ("result.status", 1)],
            name="idx_tool_status"
        )
        
        logger.info("✓ Tool calls indexes created")
        
        # ====================================================================
        # Suggestions Collection Indexes
        # ====================================================================
        suggestions = db["suggestions"]
        
        # Index: sessionId (for session suggestions)
        await suggestions.create_index(
            [("sessionId", 1)],
            name="idx_session"
        )
        
        # Index: messageId (for message-specific suggestions)
        await suggestions.create_index(
            [("messageId", 1)],
            name="idx_message"
        )
        
        # Index: userId (for user suggestions)
        await suggestions.create_index(
            [("userId", 1)],
            name="idx_user"
        )
        
        logger.info("✓ Suggestions indexes created")
        
        # ====================================================================
        # Metrics Collection Indexes
        # ====================================================================
        metrics = db["metrics"]
        
        # Compound index: sessionId + timestamp (for session metrics)
        await metrics.create_index(
            [("sessionId", 1), ("timestamp", -1)],
            name="idx_session_timestamp"
        )
        
        # Index: userId (for user metrics)
        await metrics.create_index(
            [("userId", 1)],
            name="idx_user"
        )
        
        # Index: messageId (for message-specific metrics)
        await metrics.create_index(
            [("messageId", 1)],
            name="idx_message",
            unique=True
        )
        
        # Index: timestamp (for time-based analytics)
        await metrics.create_index(
            [("timestamp", -1)],
            name="idx_timestamp"
        )
        
        logger.info("✓ Metrics indexes created")
        
        logger.info("All indexes created successfully!")
        
    except Exception as e:
        logger.error(f"Failed to create indexes: {str(e)}")
        raise


async def drop_indexes(db: AsyncIOMotorDatabase):
    """
    Drop all custom indexes (for development/testing).
    
    WARNING: This will degrade query performance.
    Only use in development environments.
    
    Args:
        db: MongoDB database instance
    """
    logger.warning("Dropping all custom indexes...")
    
    try:
        collections = ["messages", "sessions", "tool_calls", "suggestions", "metrics"]
        
        for collection_name in collections:
            collection = db[collection_name]
            # Drop all indexes except _id
            indexes = await collection.index_information()
            for index_name in indexes:
                if index_name != "_id_":
                    await collection.drop_index(index_name)
            logger.info(f"✓ Dropped indexes for {collection_name}")
        
        logger.info("All indexes dropped")
        
    except Exception as e:
        logger.error(f"Failed to drop indexes: {str(e)}")
        raise


async def list_indexes(db: AsyncIOMotorDatabase) -> dict:
    """
    List all indexes in the database.
    
    Args:
        db: MongoDB database instance
    
    Returns:
        Dictionary mapping collection names to their indexes
    """
    collections = ["messages", "sessions", "tool_calls", "suggestions", "metrics"]
    result = {}
    
    for collection_name in collections:
        collection = db[collection_name]
        indexes = await collection.index_information()
        result[collection_name] = indexes
    
    return result
