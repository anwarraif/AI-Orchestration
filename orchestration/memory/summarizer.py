"""
Message summarization for long-term memory compression.
Reduces token count while preserving key information.
"""
from typing import List, Dict, Any


async def summarize_messages(
    messages: List[Dict[str, Any]],
    target_tokens: int = 500
) -> str:
    """
    Summarize conversation history into compact text.
    
    Strategy:
    1. Extract key topics and decisions
    2. Preserve important context
    3. Compress to target token count
    
    Args:
        messages: List of message documents
        target_tokens: Target token count for summary
    
    Returns:
        Compressed summary text
    """
    if not messages:
        return ""
    
    # TODO: In production, use LLM to generate smart summary
    # For now, use simple heuristic
    
    # Count messages by role
    user_messages = [m for m in messages if m.get("role") == "user"]
    assistant_messages = [m for m in messages if m.get("role") == "assistant"]
    
    # Extract key phrases (simple keyword extraction)
    all_content = " ".join([m.get("content", "") for m in messages])
    words = all_content.split()
    
    # Build summary
    summary_parts = [
        f"Conversation history: {len(messages)} total messages",
        f"User asked about: {len(user_messages)} topics",
        f"Assistant provided: {len(assistant_messages)} responses"
    ]
    
    # Add sample topics (first and last user messages)
    if user_messages:
        first_user = user_messages[0].get("content", "")[:100]
        last_user = user_messages[-1].get("content", "")[:100]
        summary_parts.append(f"Initial topic: {first_user}...")
        if len(user_messages) > 1:
            summary_parts.append(f"Recent topic: {last_user}...")
    
    summary = " | ".join(summary_parts)
    
    # Truncate if needed to meet token target
    max_chars = target_tokens * 4  # Rough estimate
    if len(summary) > max_chars:
        summary = summary[:max_chars] + "..."
    
    return summary
