"""
System vitals endpoint.
Overall system statistics and health metrics.
"""
from fastapi import APIRouter, Depends, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
import time

from db.client import get_database
from db.models import VitalsResponse

router = APIRouter()


@router.get("", response_model=VitalsResponse)
async def get_vitals(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get system vitals and overall statistics.
    
    Returns:
        VitalsResponse with system metrics
    """
    # Calculate uptime
    start_time = request.app.state.start_time
    uptime_seconds = time.time() - start_time
    
    # Count totals
    total_sessions = await db["sessions"].count_documents({})
    total_messages = await db["messages"].count_documents({})
    total_tool_calls = await db["tool_calls"].count_documents({})
    
    # Calculate average response time
    pipeline = [
        {"$group": {"_id": None, "avg_time": {"$avg": "$total_time_ms"}}}
    ]
    cursor = db["metrics"].aggregate(pipeline)
    results = await cursor.to_list(length=1)
    avg_response_time = results[0]["avg_time"] if results else None
    
    return VitalsResponse(
        uptime_seconds=uptime_seconds,
        total_sessions=total_sessions,
        total_messages=total_messages,
        total_tool_calls=total_tool_calls,
        avg_response_time_ms=avg_response_time
    )
