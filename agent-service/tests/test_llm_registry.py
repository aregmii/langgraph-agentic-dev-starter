"""Tests for LLM Registry."""

import pytest

from app.llm import LLMRegistry, get_registry, reset_registry
from app.llm.mock_client import MockLLMClient
from app.llm.grok_client import GrokClient
from app.core.base_llm import BaseLLMClient


class TestLLMRegistry:
    """Tests for LLMRegistry class."""

    def test_register_and_get_client(self):
        """Register a client and retrieve it by role."""
        registry = LLMRegistry()
        mock_client = MockLLMClient()

        registry.register("test_role", mock_client)
        retrieved = registry.get("test_role")

        assert retrieved is mock_client

    def test_get_unknown_role_falls_back_to_default(self):
        """Unknown role should fall back to default client."""
        registry = LLMRegistry()
        default_client = MockLLMClient()

        registry.register("default", default_client)
        retrieved = registry.get("unknown_role")

        assert retrieved is default_client

    def test_get_unknown_role_no_default_raises_error(self):
        """Unknown role without default should raise ValueError."""
        registry = LLMRegistry()

        with pytest.raises(ValueError) as exc_info:
            registry.get("anything")

        assert "No LLM client registered" in str(exc_info.value)
        assert "anything" in str(exc_info.value)
        assert "default" in str(exc_info.value)

    def test_get_error_shows_available_roles(self):
        """Error message should show available roles."""
        registry = LLMRegistry()
        registry.register("planner", MockLLMClient())
        registry.register("coder", MockLLMClient())

        with pytest.raises(ValueError) as exc_info:
            registry.get("validator")

        error_msg = str(exc_info.value)
        assert "planner" in error_msg or "coder" in error_msg

    def test_list_roles(self):
        """list_roles should return all registered role names."""
        registry = LLMRegistry()
        registry.register("planner", MockLLMClient())
        registry.register("coder", MockLLMClient())
        registry.register("default", MockLLMClient())

        roles = registry.list_roles()

        assert set(roles) == {"planner", "coder", "default"}

    def test_list_roles_empty_registry(self):
        """list_roles on empty registry should return empty list."""
        registry = LLMRegistry()

        roles = registry.list_roles()

        assert roles == []

    def test_clear_removes_all_clients(self):
        """clear should remove all registered clients."""
        registry = LLMRegistry()
        registry.register("planner", MockLLMClient())
        registry.register("coder", MockLLMClient())

        registry.clear()

        assert registry.list_roles() == []

    def test_register_overwrites_existing(self):
        """Registering same role twice should overwrite."""
        registry = LLMRegistry()
        client1 = MockLLMClient()
        client2 = MockLLMClient()

        registry.register("planner", client1)
        registry.register("planner", client2)

        assert registry.get("planner") is client2


class TestRegistrySingleton:
    """Tests for singleton registry functions."""

    def setup_method(self):
        """Reset registry before each test."""
        reset_registry()

    def teardown_method(self):
        """Reset registry after each test."""
        reset_registry()

    def test_get_registry_returns_singleton(self, monkeypatch):
        """get_registry should return same instance on multiple calls."""
        monkeypatch.setenv("USE_MOCK_LLM", "true")
        reset_registry()

        registry1 = get_registry()
        registry2 = get_registry()

        assert registry1 is registry2

    def test_reset_registry_creates_new_instance(self, monkeypatch):
        """reset_registry should cause new instance on next get."""
        monkeypatch.setenv("USE_MOCK_LLM", "true")
        reset_registry()

        registry1 = get_registry()
        registry1.register("custom", MockLLMClient())

        reset_registry()
        registry2 = get_registry()

        # New instance should not have custom client
        assert registry1 is not registry2
        assert "custom" not in registry2.list_roles()

    def test_mock_mode_registers_mock_clients(self, monkeypatch):
        """USE_MOCK_LLM=true should register MockLLMClient instances."""
        monkeypatch.setenv("USE_MOCK_LLM", "true")
        reset_registry()

        registry = get_registry()

        # Should have standard roles
        assert "planner" in registry.list_roles()
        assert "coder" in registry.list_roles()
        assert "validator" in registry.list_roles()
        assert "default" in registry.list_roles()

        # Should be MockLLMClient instances
        planner_client = registry.get("planner")
        assert isinstance(planner_client, MockLLMClient)

    def test_real_mode_registers_grok_clients(self, monkeypatch):
        """USE_MOCK_LLM=false should register GrokClient instances."""
        # Set up required API key for GrokClient
        monkeypatch.setenv("XAI_API_KEY", "test-api-key")
        monkeypatch.setenv("USE_MOCK_LLM", "false")
        reset_registry()

        registry = get_registry()

        # Should have standard roles
        assert "planner" in registry.list_roles()
        assert "coder" in registry.list_roles()
        assert "validator" in registry.list_roles()
        assert "default" in registry.list_roles()

        # Should be GrokClient instances
        planner_client = registry.get("planner")
        assert isinstance(planner_client, GrokClient)

    def test_unset_mock_env_defaults_to_real(self, monkeypatch):
        """Unset USE_MOCK_LLM should default to real clients."""
        # Ensure env var is not set
        monkeypatch.delenv("USE_MOCK_LLM", raising=False)
        monkeypatch.setenv("XAI_API_KEY", "test-api-key")
        reset_registry()

        registry = get_registry()
        client = registry.get("default")

        assert isinstance(client, GrokClient)

    def test_default_fallback_works(self, monkeypatch):
        """Registry should fall back to default for unknown roles."""
        monkeypatch.setenv("USE_MOCK_LLM", "true")
        reset_registry()

        registry = get_registry()
        client = registry.get("some_new_agent_role")

        # Should get default client
        assert isinstance(client, MockLLMClient)


class TestRegistryIntegration:
    """Integration tests for registry with actual client interfaces."""

    def setup_method(self):
        """Reset registry before each test."""
        reset_registry()

    def teardown_method(self):
        """Reset registry after each test."""
        reset_registry()

    def test_registered_clients_are_base_llm_instances(self, monkeypatch):
        """All registered clients should implement BaseLLMClient."""
        monkeypatch.setenv("USE_MOCK_LLM", "true")
        reset_registry()

        registry = get_registry()

        for role in registry.list_roles():
            client = registry.get(role)
            assert isinstance(client, BaseLLMClient)

    def test_clients_have_required_methods(self, monkeypatch):
        """Registered clients should have generate and get_model_name methods."""
        monkeypatch.setenv("USE_MOCK_LLM", "true")
        reset_registry()

        registry = get_registry()
        client = registry.get("planner")

        assert hasattr(client, "generate")
        assert hasattr(client, "generate_with_context")
        assert hasattr(client, "get_model_name")
        assert callable(client.generate)
        assert callable(client.get_model_name)
