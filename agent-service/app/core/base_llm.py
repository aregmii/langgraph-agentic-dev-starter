"""
Base LLM Client Interface

This module defines the interface for LLM providers. Implementations
can wrap OpenAI, Anthropic, local models, or any other LLM.

"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMResponse:
    """
    Standardized response from any LLM provider.
    
    All implementations return this format, making it easy
    to swap providers without changing consuming code.
    """
    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    
    @property
    def cost_estimate(self) -> float:
        """
        Rough cost estimate in USD.
        
        Override in provider-specific implementations for
        accurate pricing.
        """
        # Default estimate: $0.01 per 1K tokens
        return (self.total_tokens / 1000) * 0.01


class BaseLLMClient(ABC):
    """
    Abstract base class for LLM providers.
    
    Implement this interface to add support for new LLM providers.
    The agent code depends only on this interface, not concrete
    implementations.
    
    Example implementation:
        class OpenAIClient(BaseLLMClient):
            def __init__(self, api_key: str, model: str = "gpt-4"):
                self.client = OpenAI(api_key=api_key)
                self.model = model
            
            async def generate(self, prompt: str, ...) -> LLMResponse:
                response = await self.client.chat.completions.create(...)
                return LLMResponse(content=response.choices[0].message.content, ...)
    
    Extension point: Create new implementations in agent-service/app/llm/
    """
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        """
        Generate a completion from the LLM.
        
        Args:
            prompt: The user prompt / main input
            system_prompt: Optional system instructions
            temperature: Randomness (0.0 = deterministic, 1.0 = creative)
            max_tokens: Maximum tokens in response
            
        Returns:
            LLMResponse with content and metadata
        """
        pass
    
    @abstractmethod
    async def generate_with_context(
        self,
        prompt: str,
        context: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        """
        Generate a completion with additional context.
        
        Useful for code repair where existing code is provided
        as context.
        
        Args:
            prompt: The user prompt / instruction
            context: Additional context (e.g., existing code, error messages)
            system_prompt: Optional system instructions
            temperature: Randomness (0.0 = deterministic, 1.0 = creative)
            max_tokens: Maximum tokens in response
            
        Returns:
            LLMResponse with content and metadata
        """
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """Return the model identifier (e.g., 'gpt-4', 'claude-3-opus')."""
        pass