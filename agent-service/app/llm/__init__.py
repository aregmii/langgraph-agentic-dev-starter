"""LLM Client Factory"""

import os


def get_llm_client():
    """
    Get the appropriate LLM client based on environment.

    Set USE_MOCK_LLM=true for testing without API calls.
    """
    use_mock = os.getenv("USE_MOCK_LLM", "false").lower() == "true"

    if use_mock:
        from app.llm.mock_client import MockLLMClient
        print("🧪 Using MOCK LLM Client (no API calls)")
        return MockLLMClient(latency_ms=100)
    else:
        from app.llm.grok_client import GrokClient
        print("🔥 Using REAL Grok LLM Client")
        return GrokClient()
