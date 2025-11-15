"""
Metrics and analytics endpoints.
Performance metrics, timing data, and tool usage stats.
"""
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional

from db.client import get_database
from db.models import MetricsResponse

router = APIRouter()


@router.get("/{session_id}", response_model=MetricsResponse)
async def get_session_metrics(
    session_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get aggregated metrics for a session.
    
    Calculates:
    - Total requests
    - Average TTFT (Time To First Token)
    - Average total time
    - Total tool calls
    
    Args:
        session_id: Session identifier
    
    Returns:
        MetricsResponse with aggregated stats
    """
    # Aggregate metrics using MongoDB pipeline
    pipeline = [
        {"$match": {"sessionId": session_id}},
        {
            "$group": {
                "_id": "$sessionId",
                "totalRequests": {"$sum": 1},
                "avgTtftMs": {"$avg": "$ttft_ms"},
                "avgTotalTimeMs": {"$avg": "$total_time_ms"},
                "totalToolCalls": {"$sum": "$tool_call_count"}
            }
        }
    ]
    
    cursor = db["metrics"].aggregate(pipeline)
    results = await cursor.to_list(length=1)
    
    if not results:
        return MetricsResponse(
            sessionId=session_id,
            totalRequests=0,
            avgTtftMs=None,
            avgTotalTimeMs=None,
            totalToolCalls=0
        )
    
    result = results[0]
    
    return MetricsResponse(
        sessionId=session_id,
        totalRequests=result["totalRequests"],
        avgTtftMs=result.get("avgTtftMs"),
        avgTotalTimeMs=result.get("avgTotalTimeMs"),
        totalToolCalls=result["totalToolCalls"]
    )
