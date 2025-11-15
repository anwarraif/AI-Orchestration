"""
Real LLM provider integration (OpenAI, Anthropic, etc.).
Designed with toggle capability between mock and real providers.
"""
from typing import AsyncIterator, Optional
import os
from enum import Enum

from .mock import MockLLM


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    MOCK = "mock"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class LLMClient:
    """
    Unified LLM client with provider abstraction.
    
    Supports:
    - Mock LLM (default for development)
    - OpenAI GPT models
    - Anthropic Claude models
    
    Usage:
        client = LLMClient(provider="openai")
        async for token in client.stream("Hello"):
            print(token)
    """
    
    def __init__(
        self,
        provider: str = "mock",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize LLM client.
        
        Args:
            provider: Provider name ("mock", "openai", "anthropic")
            model: Model name (e.g., "gpt-4", "claude-3-sonnet")
            api_key: API key (defaults to environment variable)
            **kwargs: Additional provider-specific parameters
        """
        self.provider = LLMProvider(provider)
        self.model = model
        self.api_key = api_key or os.getenv(f"{provider.upper()}_API_KEY")
        self.kwargs = kwargs
        
        # Initialize provider client
        if self.provider == LLMProvider.MOCK:
            self.client = MockLLM()
        elif self.provider == LLMProvider.OPENAI:
            self._init_openai()
        elif self.provider == LLMProvider.ANTHROPIC:
            self._init_anthropic()
    
    def _init_openai(self):
        """Initialize OpenAI client."""
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(api_key=self.api_key)
            self.model = self.model or "gpt-4-turbo-preview"
        except ImportError:
            raise ImportError("OpenAI package not installed. Run: pip install openai")
    
    def _init_anthropic(self):
        """Initialize Anthropic client."""
        try:
            from anthropic import AsyncAnthropic
            self.client = AsyncAnthropic(api_key=self.api_key)
            self.model = self.model or "claude-3-sonnet-20240229"
        except ImportError:
            raise ImportError("Anthropic package not installed. Run: pip install anthropic")
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate complete response (non-streaming).
        
        Args:
            prompt: Input prompt
            **kwargs: Generation parameters (temperature, max_tokens, etc.)
        
        Returns:
            Complete response text
        """
        if self.provider == LLMProvider.MOCK:
            return await self.client.generate(prompt, **kwargs)
        
        elif self.provider == LLMProvider.OPENAI:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                **{**self.kwargs, **kwargs}
            )
            return response.choices[0].message.content
        
        elif self.provider == LLMProvider.ANTHROPIC:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=kwargs.get("max_tokens", 1024),
                messages=[{"role": "user", "content": prompt}],
                **{**self.kwargs, **kwargs}
            )
            return response.content[0].text
    
    async def stream(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        """
        Generate streaming response token by token.
        
        Args:
            prompt: Input prompt
            **kwargs: Generation parameters
        
        Yields:
            Individual tokens
        """
        if self.provider == LLMProvider.MOCK:
            async for token in self.client.stream(prompt, **kwargs):
                yield token
        
        elif self.provider == LLMProvider.OPENAI:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
                **{**self.kwargs, **kwargs}
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        
        elif self.provider == LLMProvider.ANTHROPIC:
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=kwargs.get("max_tokens", 1024),
                messages=[{"role": "user", "content": prompt}],
                **{**self.kwargs, **kwargs}
            ) as stream:
                async for text in stream.text_stream:
                    yield text


# Default client factory
def create_llm_client(provider: Optional[str] = None) -> LLMClient:
    """
    Factory function to create LLM client from environment.
    
    Args:
        provider: Override provider (defaults to env var LLM_PROVIDER)
    
    Returns:
        Configured LLMClient instance
    """
    provider = provider or os.getenv("LLM_PROVIDER", "mock")
    return LLMClient(provider=provider)
