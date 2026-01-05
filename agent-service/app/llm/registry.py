"""
LLM Registry for multi-agent systems.

Provides a centralized registry for LLM clients, allowing different agents
(Planner, Coder, Validator) to use different LLM configurations optimized
for their specific tasks.

Usage:
    from app.llm import get_registry

    # Get client for a specific role
    planner_llm = get_registry().get("planner")
    coder_llm = get_registry().get("coder")

    # Register custom client
    get_registry().register("custom", my_custom_client)
"""

import os
from typing import Optional

from app.core.base_llm import BaseLLMClient


class LLMRegistry:
    """
    Registry for managing LLM clients by role.

    Allows different agents to use different LLM configurations.
    For example, a planner might use a model optimized for reasoning,
    while a coder uses one optimized for code generation.

    Example:
        >>> registry = LLMRegistry()
        >>> registry.register("planner", planner_client)
        >>> registry.register("coder", coder_client)
        >>> registry.get("planner")  # Returns planner_client
        >>> registry.get("unknown")  # Falls back to "default" if registered
    """

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._clients: dict[str, BaseLLMClient] = {}

    def register(self, role: str, client: BaseLLMClient) -> None:
        """
        Register an LLM client for a specific role.

        Args:
            role: Role name (e.g., "planner", "coder", "validator", "default")
            client: LLM client instance implementing BaseLLMClient
        """
        self._clients[role] = client

    def get(self, role: str) -> BaseLLMClient:
        """
        Get the LLM client for a specific role.

        If the requested role is not found, falls back to "default".

        Args:
            role: Role name to look up

        Returns:
            BaseLLMClient instance for the role

        Raises:
            ValueError: If role not found and no "default" registered
        """
        if role in self._clients:
            return self._clients[role]

        if "default" in self._clients:
            return self._clients["default"]

        available = list(self._clients.keys()) if self._clients else []
        raise ValueError(
            f"No LLM client registered for role '{role}' and no 'default' available. "
            f"Available roles: {available}"
        )

    def list_roles(self) -> list[str]:
        """
        List all registered role names.

        Returns:
            List of role names that have registered clients
        """
        return list(self._clients.keys())

    def clear(self) -> None:
        """
        Remove all registered clients.

        Useful for testing to reset state between tests.
        """
        self._clients.clear()


# Module-level singleton
_registry: Optional[LLMRegistry] = None


def get_registry() -> LLMRegistry:
    """
    Get the singleton LLM registry instance.

    Lazily initializes the registry with default clients on first call.

    Returns:
        The global LLMRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = _init_default_registry()
    return _registry


def _init_default_registry() -> LLMRegistry:
    """
    Create and initialize a registry with default LLM clients.

    Environment variables:
    - USE_MOCK_LLM=true: Use mock client (no API calls)
    - OPENROUTER_API_KEY: Required for real LLM calls
    - OPENROUTER_MODEL: Model to use (default: FREE model)

    IMPORTANT: Always uses FREE models by default to avoid spending credits!

    Returns:
        Initialized LLMRegistry with clients for standard roles
    """
    registry = LLMRegistry()

    use_mock = os.getenv("USE_MOCK_LLM", "false").lower() == "true"

    # Standard roles used by agents
    roles = ["planner", "coder", "validator", "default"]

    if use_mock:
        from app.llm.mock_client import MockLLMClient

        # Create shared mock client (lightweight, can share)
        mock_client = MockLLMClient(latency_ms=100)

        for role in roles:
            registry.register(role, mock_client)
    else:
        # Always use OpenRouter with FREE models
        if not os.getenv("OPENROUTER_API_KEY"):
            raise ValueError(
                "OPENROUTER_API_KEY not set. Add it to .env file.\n"
                "Get a key at: https://openrouter.ai/keys"
            )

        from app.llm.openrouter_client import OpenRouterClient

        # DEFAULT TO FREE MODEL - never use paid models without explicit config
        model = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-exp:free")
        client = OpenRouterClient(model=model)

        for role in roles:
            registry.register(role, client)

    return registry


def reset_registry() -> None:
    """
    Reset the singleton registry.

    The next call to get_registry() will create a fresh instance
    with default clients based on current environment variables.

    Useful for testing to ensure clean state between tests.
    """
    global _registry
    _registry = None
