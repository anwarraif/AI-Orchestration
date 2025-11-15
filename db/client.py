"""
MongoDB connection management with async motor.
Provides singleton database client and connection lifecycle.
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional
import os
import logging

logger = logging.getLogger(__name__)


class DatabaseClient:
    """
    MongoDB client wrapper with connection pooling.
    
    Usage:
        db_client = DatabaseClient()
        await db_client.connect()
        db = db_client.get_database()
        # ... use db
        await db_client.disconnect()
    """
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        self._connected = False
    
    async def connect(
        self,
        connection_string: Optional[str] = None,
        database_name: Optional[str] = None
    ):
        """
        Establish connection to MongoDB.
        
        Args:
            connection_string: MongoDB URI (defaults to env MONGO_URI)
            database_name: Database name (defaults to env MONGO_DB_NAME)
        """
        if self._connected:
            logger.warning("Database already connected")
            return
        
        # Get connection details from env or parameters
        connection_string = connection_string or os.getenv(
            "MONGO_URI",
            "mongodb://localhost:27017"
        )
        database_name = database_name or os.getenv(
            "MONGO_DB_NAME",
            "ai_orchestration"
        )
        
        try:
            # Create client with connection pooling
            self.client = AsyncIOMotorClient(
                connection_string,
                maxPoolSize=10,
                minPoolSize=2,
                serverSelectionTimeoutMS=5000
            )
            
            # Get database
            self.db = self.client[database_name]
            
            # Test connection
            await self.db.command("ping")
            
            self._connected = True
            logger.info(f"Connected to MongoDB: {database_name}")
        
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise
    
    async def disconnect(self):
        """Close MongoDB connection."""
        if self.client and self._connected:
            self.client.close()
            self._connected = False
            logger.info("Disconnected from MongoDB")
    
    def get_database(self) -> AsyncIOMotorDatabase:
        """
        Get database instance.
        
        Returns:
            AsyncIOMotorDatabase instance
        
        Raises:
            RuntimeError: If not connected
        """
        if not self._connected or self.db is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self.db
    
    def is_connected(self) -> bool:
        """Check if database is connected."""
        return self._connected
    
    async def health_check(self) -> bool:
        """
        Check database health.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            if not self._connected:
                return False
            await self.db.command("ping")
            return True
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False


# Global singleton instance
_db_client: Optional[DatabaseClient] = None


def get_db_client() -> DatabaseClient:
    """
    Get global database client instance (singleton).
    
    Returns:
        DatabaseClient instance
    """
    global _db_client
    if _db_client is None:
        _db_client = DatabaseClient()
    return _db_client


async def get_database() -> AsyncIOMotorDatabase:
    """
    Dependency injection helper for FastAPI.
    
    Returns:
        AsyncIOMotorDatabase instance
    
    Usage in FastAPI:
        @app.get("/")
        async def endpoint(db: AsyncIOMotorDatabase = Depends(get_database)):
            ...
    """
    client = get_db_client()
    if not client.is_connected():
        await client.connect()
    return client.get_database()
