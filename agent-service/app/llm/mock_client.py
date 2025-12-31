"""
Mock LLM Client

Returns fake but valid responses for testing without API calls.
Enable with: USE_MOCK_LLM=true
"""

import asyncio
from app.core.base_llm import BaseLLMClient, LLMResponse


MOCK_RESPONSES = {
    "identify": "CODE_GENERATION",
    "can_handle": "YES",
    "code": '''def hello_world(name: str = "World") -> str:
    """Return a greeting message."""
    return f"Hello, {name}!"


if __name__ == "__main__":
    print(hello_world())
    print(hello_world("Developer"))
''',
}


class MockLLMClient(BaseLLMClient):
    """Mock LLM client for testing."""

    def __init__(self, latency_ms: float = 100):
        self.latency_ms = latency_ms

    async def _simulate_latency(self):
        if self.latency_ms > 0:
            await asyncio.sleep(self.latency_ms / 1000)

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        await self._simulate_latency()

        prompt_lower = prompt.lower()

        if "yes or no" in prompt_lower or "can you handle" in prompt_lower:
            content = MOCK_RESPONSES["can_handle"]
        elif "classify" in prompt_lower or "task type" in prompt_lower:
            content = MOCK_RESPONSES["identify"]
        else:
            content = MOCK_RESPONSES["code"]

        prompt_tokens = len(prompt.split())
        completion_tokens = len(content.split())

        return LLMResponse(
            content=content,
            model="mock-llm",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )

    async def generate_with_context(
        self,
        prompt: str,
        context: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        return await self.generate(prompt, system_prompt, temperature, max_tokens)

    def get_model_name(self) -> str:
        return "mock-llm"
