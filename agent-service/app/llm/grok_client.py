"""
Grok (xAI) Client Implementation

Implements BaseLLMClient for xAI's Grok API.
Free API key at: https://console.x.ai/
"""

import os
from openai import AsyncOpenAI
from app.core.base_llm import BaseLLMClient, LLMResponse
from pathlib import Path

def load_env():
    env_path = Path(__file__).parent.parent.parent.parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ.setdefault(key, value)

load_env()

class GrokClient(BaseLLMClient):
    """
    Grok implementation of BaseLLMClient.
    
    Uses xAI's OpenAI-compatible API.
    Requires XAI_API_KEY environment variable.
    """
    
    def __init__(self, model: str = "grok-3"):
        self.model = model
        api_key = os.getenv("XAI_API_KEY")
        if not api_key:
            raise ValueError("XAI_API_KEY environment variable not set")
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1",  # xAI's endpoint
        )
    
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        """Generate a completion from Grok."""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        return LLMResponse(
            content=response.choices[0].message.content or "",
            model=self.model,
            prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
            completion_tokens=response.usage.completion_tokens if response.usage else 0,
            total_tokens=response.usage.total_tokens if response.usage else 0,
        )
    
    async def generate_with_context(
        self,
        prompt: str,
        context: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        """Generate with additional context."""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({
            "role": "system",
            "content": f"Reference code/context:\n\n{context}"
        })
        
        messages.append({"role": "user", "content": prompt})
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        return LLMResponse(
            content=response.choices[0].message.content or "",
            model=self.model,
            prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
            completion_tokens=response.usage.completion_tokens if response.usage else 0,
            total_tokens=response.usage.total_tokens if response.usage else 0,
        )
    
    def get_model_name(self) -> str:
        return self.model