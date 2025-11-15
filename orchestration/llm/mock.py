"""
Mock LLM provider for testing and development.
Returns predefined responses without external API calls.
"""
from typing import AsyncIterator, List, Dict, Any
import asyncio


class MockLLM:
    """
    Mock LLM that simulates streaming responses.
    
    Usage:
        llm = MockLLM()
        async for token in llm.stream("Hello"):
            print(token)
    """
    
    def __init__(self, delay_ms: int = 50):
        """
        Initialize mock LLM.
        
        Args:
            delay_ms: Delay between tokens (milliseconds) to simulate streaming
        """
        self.delay_ms = delay_ms
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate complete response (non-streaming).
        
        Args:
            prompt: Input prompt
            **kwargs: Additional generation parameters (ignored)
        
        Returns:
            Complete response text
        """
        # Simple mock logic based on prompt keywords
        prompt_lower = prompt.lower()
        
        if "summarize" in prompt_lower or "summary" in prompt_lower:
            return "Here's a summary of the key points discussed: The conversation covered multiple topics with detailed analysis. Main findings include successful execution of tasks and validation of results."
        
        elif "plan" in prompt_lower or "steps" in prompt_lower:
            return "I'll break this down into steps: 1) Analyze the requirements, 2) Gather necessary data, 3) Process and validate information."
        
        elif "validate" in prompt_lower or "check" in prompt_lower:
            return "Validation complete. All checks passed successfully. The output meets quality standards."
        
        else:
            return f"Mock response to: {prompt[:50]}... The analysis has been completed with relevant findings."
    
    async def stream(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        """
        Generate streaming response token by token.
        
        Args:
            prompt: Input prompt
            **kwargs: Additional generation parameters (ignored)
        
        Yields:
            Individual tokens (words/phrases)
        """
        # Get full response
        full_response = await self.generate(prompt, **kwargs)
        
        # Split into tokens (words)
        tokens = full_response.split()
        
        # Stream tokens with delay
        for token in tokens:
            await asyncio.sleep(self.delay_ms / 1000)
            yield token + " "
    
    def count_tokens(self, text: str) -> int:
        """
        Estimate token count (simple word count).
        
        Args:
            text: Input text
        
        Returns:
            Estimated token count
        """
        return len(text.split())
