"""
Time utilities for consistent timestamp handling across the system.
"""
from datetime import datetime, timezone
from typing import Optional


def utc_now() -> datetime:
    """
    Get current UTC time as timezone-aware datetime.
    
    Returns:
        datetime: Current UTC time with timezone info
    """
    return datetime.now(timezone.utc)


def utc_timestamp() -> float:
    """
    Get current UTC time as Unix timestamp (seconds).
    
    Returns:
        float: Unix timestamp in seconds
    """
    return utc_now().timestamp()


def utc_timestamp_ms() -> int:
    """
    Get current UTC time as Unix timestamp in milliseconds.
    
    Returns:
        int: Unix timestamp in milliseconds
    """
    return int(utc_timestamp() * 1000)


def format_iso(dt: Optional[datetime] = None) -> str:
    """
    Format datetime as ISO 8601 string.
    
    Args:
        dt: datetime to format, defaults to current UTC time
    
    Returns:
        str: ISO 8601 formatted string (e.g., "2025-11-12T10:30:00.000Z")
    """
    if dt is None:
        dt = utc_now()
    return dt.isoformat()


def calculate_ttft(request_start: float, first_token_at: Optional[float]) -> Optional[float]:
    """
    Calculate Time To First Token (TTFT) in milliseconds.
    
    Args:
        request_start: Request start timestamp (seconds)
        first_token_at: First token emission timestamp (seconds)
    
    Returns:
        float: TTFT in milliseconds, or None if first_token_at is None
    """
    if first_token_at is None:
        return None
    return (first_token_at - request_start) * 1000


def calculate_total_time(request_start: float, completed_at: Optional[float]) -> Optional[float]:
    """
    Calculate total request time in milliseconds.
    
    Args:
        request_start: Request start timestamp (seconds)
        completed_at: Request completion timestamp (seconds)
    
    Returns:
        float: Total time in milliseconds, or None if completed_at is None
    """
    if completed_at is None:
        return None
    return (completed_at - request_start) * 1000
