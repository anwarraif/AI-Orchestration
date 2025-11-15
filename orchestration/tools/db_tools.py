"""
Database tools for agent invocation.
Provides db.find, db.insert, db.aggregate with logging and metrics.
"""
from typing import Dict, Any, List, Optional
import time
from datetime import datetime


class DBToolError(Exception):
    """Custom exception for DB tool errors."""
    pass


class DBTools:
    """
    Database tool wrapper for agent use.
    Logs all invocations for observability and metrics.
    """
    
    def __init__(self, db_client):
        """
        Initialize DB tools with MongoDB client.
        
        Args:
            db_client: MongoDB database instance from motor
        """
        self.db = db_client
        self.tool_call_logs: List[Dict[str, Any]] = []

    async def find(self, collection, filter, limit=None, projection=None):
        """
        Returns:
            (result_dict, latency_ms)
        """
        start_time = time.time()
        tool_name = "db.find"

        try:
            cursor = self.db[collection].find(filter, projection)
            if limit:
                cursor = cursor.limit(limit)

            data = await cursor.to_list(length=limit)
            latency_ms = (time.time() - start_time) * 1000

            result = {
                "status": "ok",
                "count": len(data),
                "data": data
            }

            # log entry
            self.tool_call_logs.append({
                "tool": tool_name,
                "args": {
                    "collection": collection,
                    "filter": filter,
                    "limit": limit
                },
                "result": result,
                "latency_ms": latency_ms,
                "timestamp": datetime.utcnow().isoformat()
            })

            return result, latency_ms

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000

            result = {
                "status": "error",
                "error": str(e)
            }

            self.tool_call_logs.append({
                "tool": tool_name,
                "args": {
                    "collection": collection,
                    "filter": filter,
                    "limit": limit
                },
                "result": result,
                "latency_ms": latency_ms,
                "timestamp": datetime.utcnow().isoformat()
            })

            raise DBToolError(str(e))
    
    # async def find(
    #     self,
    #     collection: str,
    #     filter: Dict[str, Any],
    #     limit: Optional[int] = None,
    #     projection: Optional[Dict[str, Any]] = None
    # ) -> Dict[str, Any]:
    #     """
    #     Execute db.find query with logging.
        
    #     Args:
    #         collection: Collection name
    #         filter: MongoDB filter query
    #         limit: Optional limit
    #         projection: Optional field projection
        
    #     Returns:
    #         {
    #             "status": "ok" | "error",
    #             "count": int,
    #             "data": List[Dict],
    #             "latency_ms": float
    #         }
    #     """
    #     start_time = time.time()
    #     tool_name = "db.find"
        
    #     try:
    #         # Build query
    #         cursor = self.db[collection].find(filter, projection)
    #         if limit:
    #             cursor = cursor.limit(limit)
            
    #         # Execute
    #         results = await cursor.to_list(length=limit)
            
    #         # Calculate latency
    #         latency_ms = (time.time() - start_time) * 1000
            
    #         # Log tool call
    #         log_entry = {
    #             "tool": tool_name,
    #             "args": {
    #                 "collection": collection,
    #                 "filter": filter,
    #                 "limit": limit,
    #                 "projection": projection
    #             },
    #             "result": {
    #                 "status": "ok",
    #                 "count": len(results)
    #             },
    #             "latency_ms": latency_ms,
    #             "timestamp": datetime.utcnow().isoformat()
    #         }
    #         self.tool_call_logs.append(log_entry)
            
    #         return {
    #             "status": "ok",
    #             "count": len(results),
    #             "data": results,
    #             "latency_ms": latency_ms
    #         }
        
    #     except Exception as e:
    #         latency_ms = (time.time() - start_time) * 1000
            
    #         # Log error
    #         log_entry = {
    #             "tool": tool_name,
    #             "args": {
    #                 "collection": collection,
    #                 "filter": filter,
    #                 "limit": limit
    #             },
    #             "result": {
    #                 "status": "error",
    #                 "error": str(e)
    #             },
    #             "latency_ms": latency_ms,
    #             "timestamp": datetime.utcnow().isoformat()
    #         }
    #         self.tool_call_logs.append(log_entry)
            
    #         raise DBToolError(f"db.find failed: {str(e)}")
    
    async def insert(
        self,
        collection: str,
        document: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute db.insert with logging.
        
        Args:
            collection: Collection name
            document: Document to insert
        
        Returns:
            {
                "status": "ok" | "error",
                "inserted_id": str,
                "latency_ms": float
            }
        """
        start_time = time.time()
        tool_name = "db.insert"
        
        try:
            # Execute insert
            result = await self.db[collection].insert_one(document)
            
            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000
            
            # Log tool call
            log_entry = {
                "tool": tool_name,
                "args": {
                    "collection": collection,
                    "document_keys": list(document.keys())
                },
                "result": {
                    "status": "ok",
                    "inserted_id": str(result.inserted_id)
                },
                "latency_ms": latency_ms,
                "timestamp": datetime.utcnow().isoformat()
            }
            self.tool_call_logs.append(log_entry)
            
            return {
                "status": "ok",
                "inserted_id": str(result.inserted_id),
                "latency_ms": latency_ms
            }
        
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            
            # Log error
            log_entry = {
                "tool": tool_name,
                "args": {
                    "collection": collection,
                    "document_keys": list(document.keys())
                },
                "result": {
                    "status": "error",
                    "error": str(e)
                },
                "latency_ms": latency_ms,
                "timestamp": datetime.utcnow().isoformat()
            }
            self.tool_call_logs.append(log_entry)
            
            raise DBToolError(f"db.insert failed: {str(e)}")
    
    async def aggregate(
        self,
        collection: str,
        pipeline: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Execute db.aggregate with logging.
        
        Args:
            collection: Collection name
            pipeline: Aggregation pipeline
        
        Returns:
            {
                "status": "ok" | "error",
                "count": int,
                "data": List[Dict],
                "latency_ms": float
            }
        """
        start_time = time.time()
        tool_name = "db.aggregate"
        
        try:
            # Execute aggregation
            cursor = self.db[collection].aggregate(pipeline)
            results = await cursor.to_list(length=None)
            
            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000
            
            # Log tool call
            log_entry = {
                "tool": tool_name,
                "args": {
                    "collection": collection,
                    "pipeline_stages": len(pipeline)
                },
                "result": {
                    "status": "ok",
                    "count": len(results)
                },
                "latency_ms": latency_ms,
                "timestamp": datetime.utcnow().isoformat()
            }
            self.tool_call_logs.append(log_entry)
            
            return {
                "status": "ok",
                "count": len(results),
                "data": results,
                "latency_ms": latency_ms
            }
        
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            
            # Log error
            log_entry = {
                "tool": tool_name,
                "args": {
                    "collection": collection,
                    "pipeline_stages": len(pipeline)
                },
                "result": {
                    "status": "error",
                    "error": str(e)
                },
                "latency_ms": latency_ms,
                "timestamp": datetime.utcnow().isoformat()
            }
            self.tool_call_logs.append(log_entry)
            
            raise DBToolError(f"db.aggregate failed: {str(e)}")
    
    def get_tool_logs(self) -> List[Dict[str, Any]]:
        """Return all tool call logs for metrics."""
        return self.tool_call_logs
    
    def clear_logs(self):
        """Clear tool call logs."""
        self.tool_call_logs = []
