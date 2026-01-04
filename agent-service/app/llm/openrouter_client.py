"""
OpenRouter Client Implementation

Implements BaseLLMClient for OpenRouter API.
Provides access to many models (Claude, GPT-4, Llama, Mistral, etc.)

Get API key at: https://openrouter.ai/keys

Popular models:
- anthropic/claude-3.5-sonnet (recommended for code)
- anthropic/claude-3-haiku (fast, cheap)
- openai/gpt-4o
- openai/gpt-4o-mini (fast, cheap)
- meta-llama/llama-3.1-70b-instruct
- google/gemini-pro-1.5
"""

import os
from openai import AsyncOpenAI
from app.core.base_llm import BaseLLMClient, LLMResponse
from pathlib import Path


def load_env():
    """Load .env file, OVERRIDING any existing environment variables."""
    env_path = Path(__file__).parent.parent.parent.parent / ".env"

    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    value = value.strip().strip('"').strip("'")
                    os.environ[key] = value


load_env()


class OpenRouterClient(BaseLLMClient):
    """
    OpenRouter implementation of BaseLLMClient.

    Uses OpenRouter's OpenAI-compatible API to access multiple model providers.
    Requires OPENROUTER_API_KEY environment variable.

    Args:
        model: Model ID from OpenRouter (default: anthropic/claude-3.5-sonnet)
               See https://openrouter.ai/models for full list
    """

    def __init__(self, model: str = "anthropic/claude-3.5-sonnet"):
        self.model = model
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENROUTER_API_KEY environment variable not set. "
                "Get your key at https://openrouter.ai/keys"
            )
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
        )

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        """Generate a completion from OpenRouter."""
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
