"""LLM Client Factory and Registry"""

import os
from pathlib import Path

from .registry import LLMRegistry, get_registry, reset_registry


def _load_env():
    """Load .env file from project root."""
    env_path = Path(__file__).parent.parent.parent.parent / ".env"

    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    value = value.strip().strip('"').strip("'")
                    os.environ[key] = value


_load_env()


def get_llm_client():
    """
    Get the appropriate LLM client based on environment.

    Environment variables:
    - USE_MOCK_LLM=true: Use mock client (no API calls)
    - LLM_PROVIDER=openrouter: Use OpenRouter (default if OPENROUTER_API_KEY set)
    - LLM_PROVIDER=grok: Use xAI Grok
    - OPENROUTER_MODEL: Model to use with OpenRouter (default: anthropic/claude-3.5-sonnet)

    Note: This function is kept for backwards compatibility.
    New code should use get_registry().get("role") instead.
    """
    use_mock = os.getenv("USE_MOCK_LLM", "false").lower() == "true"

    if use_mock:
        from app.llm.mock_client import MockLLMClient
        print("🧪 Using MOCK LLM Client (no API calls)")
        return MockLLMClient(latency_ms=100)

    # Determine provider
    provider = os.getenv("LLM_PROVIDER", "").lower()

    # Auto-detect based on available API keys if not specified
    if not provider:
        if os.getenv("OPENROUTER_API_KEY"):
            provider = "openrouter"
        elif os.getenv("XAI_API_KEY"):
            provider = "grok"
        else:
            raise ValueError(
                "No LLM API key found. Set one of:\n"
                "  - OPENROUTER_API_KEY (recommended)\n"
                "  - XAI_API_KEY (for Grok)"
            )

    if provider == "openrouter":
        from app.llm.openrouter_client import OpenRouterClient
        model = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")
        print(f"🌐 Using OpenRouter with model: {model}")
        return OpenRouterClient(model=model)
    elif provider == "grok":
        from app.llm.grok_client import GrokClient
        print("🔥 Using xAI Grok LLM Client")
        return GrokClient()
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider}")


__all__ = [
    "get_llm_client",
    "LLMRegistry",
    "get_registry",
    "reset_registry",
]
