"""
Context manager for packing conversation history with token budget management.
Implements the context packing strategy defined in requirements.
"""
from typing import List, Dict, Any, Optional
import math

from .store import MemoryStore
from .summarizer import summarize_messages


# Configuration
DEFAULT_SHORT_TERM_K = 10  # Last K turns to include
DEFAULT_TOKEN_BUDGET = 3000  # Max tokens for context
CHARS_PER_TOKEN = 4  # Token estimation: ceil(len(chars)/4)


def estimate_tokens(text: str) -> int:
    """
    Estimate token count from text using simple heuristic.
    
    Formula: ceil(len(chars) / 4)
    
    Args:
        text: Input text
    
    Returns:
        Estimated token count
    """
    return math.ceil(len(text) / CHARS_PER_TOKEN)


class ContextManager:
    """
    Manages context packing with token budgeting.
    
    Packing strategy:
    [system meta]
    [session summary (if present)]
    [last K user/assistant turns]
    [current user prompt]
    """
    
    def __init__(
        self,
        memory_store: MemoryStore,
        short_term_k: int = DEFAULT_SHORT_TERM_K,
        token_budget: int = DEFAULT_TOKEN_BUDGET
    ):
        """
        Initialize context manager.
        
        Args:
            memory_store: Memory store instance
            short_term_k: Number of recent turns to include
            token_budget: Maximum token budget for context
        """
        self.memory_store = memory_store
        self.short_term_k = short_term_k
        self.token_budget = token_budget
    
    async def pack_context(
        self,
        session_id: str,
        user_id: str,
        current_prompt: str
    ) -> Dict[str, Any]:
        """
        Pack context with token budget management.
        
        Returns packed context and metadata:
        {
            "context": str,  # Full packed context
            "summary": Optional[str],  # Session summary if exists
            "last_k_turns": List[Dict],  # Recent messages
            "token_count": int,  # Estimated tokens
            "summary_updated": bool  # True if summary was regenerated
        }
        
        Args:
            session_id: Session identifier
            user_id: User identifier
            current_prompt: Current user message
        
        Returns:
            Packed context dictionary
        """
        # Get session summary
        summary = await self.memory_store.get_session_summary(session_id)
        
        # Get last K messages
        recent_messages = await self.memory_store.get_session_messages(
            session_id,
            limit=self.short_term_k
        )
        
        # Build context parts
        system_meta = "You are a helpful AI assistant. Answer based on conversation history and current request."
        
        context_parts = [system_meta]
        
        # Add summary if exists
        if summary:
            context_parts.append(f"\n[Session Summary]\n{summary}")
        
        # Add recent turns
        if recent_messages:
            turns_text = "\n[Recent Conversation]"
            for msg in recent_messages:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                turns_text += f"\n{role.upper()}: {content}"
            context_parts.append(turns_text)
        
        # Add current prompt
        context_parts.append(f"\n[Current Request]\nUSER: {current_prompt}")
        
        # Join and estimate tokens
        full_context = "\n".join(context_parts)
        token_count = estimate_tokens(full_context)
        
        # Check if we need to update summary (exceeded budget)
        summary_updated = False
        if token_count > self.token_budget and len(recent_messages) > self.short_term_k:
            # Generate new summary from all messages
            all_messages = await self.memory_store.get_session_messages(session_id)
            new_summary = await summarize_messages(all_messages, target_tokens=500)
            
            # Save new summary
            await self.memory_store.update_session_summary(
                session_id,
                new_summary,
                user_id
            )
            
            # Rebuild context with new summary
            context_parts[1] = f"\n[Session Summary]\n{new_summary}"
            full_context = "\n".join(context_parts)
            token_count = estimate_tokens(full_context)
            summary_updated = True
            summary = new_summary
        
        return {
            "context": full_context,
            "summary": summary,
            "last_k_turns": [
                {
                    "role": msg.get("role"),
                    "content": msg.get("content"),
                    "timestamp": msg.get("timestamp")
                }
                for msg in recent_messages
            ],
            "token_count": token_count,
            "summary_updated": summary_updated
        }
