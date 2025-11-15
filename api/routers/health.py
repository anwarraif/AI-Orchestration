"""
Health check endpoint for monitoring and liveness probes.
"""
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from db.client import get_database
from db.models import HealthResponse
from orchestration.tools.time import format_iso

router = APIRouter()


@router.get("", response_model=HealthResponse)
async def health_check(db: AsyncIOMotorDatabase = Depends(get_database)):
    """
    Health check endpoint.
    
    Returns:
        HealthResponse with system status
    """
    # Check database
    try:
        await db.command("ping")
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    
    status = "healthy" if db_status == "connected" else "unhealthy"
    
    return HealthResponse(
        status=status,
        database=db_status,
        timestamp=format_iso()
    )
