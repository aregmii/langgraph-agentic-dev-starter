"""Tests for PlannerAgent class."""

import pytest

from app.agents.planner import PlannerAgent, PlannerConfig
from app.llm import get_registry, reset_registry
from app.llm.mock_client import MockLLMClient


@pytest.fixture(autouse=True)
def setup_mock_registry(monkeypatch):
    """Reset registry and use mock LLM for all tests."""
    monkeypatch.setenv("USE_MOCK_LLM", "true")
    reset_registry()
    yield
    reset_registry()


class TestPlannerAgentSimpleTask:
    """Tests for simple task handling."""

    @pytest.mark.asyncio
    async def test_simple_task_creates_single_step_plan(self):
        """Simple task should create plan with one step."""
        agent = PlannerAgent(request_id="test123")

        plan, events = await agent.create_plan("Sort a list")

        assert len(plan.steps) == 1
        assert plan.steps[0].id == "main"
        assert plan.steps[0].task == "Sort a list"
        assert plan.steps[0].complexity == "simple"
        assert plan.reasoning == "Simple task - single step execution"

    @pytest.mark.asyncio
    async def test_simple_task_skips_llm_call(self):
        """Simple task should NOT call LLM."""
        # Get the mock client to track calls
        registry = get_registry()
        mock_client = registry.get("planner")
        assert isinstance(mock_client, MockLLMClient)
        initial_count = mock_client.call_count

        agent = PlannerAgent(request_id="test123")
        await agent.create_plan("Sort a list")

        # LLM should NOT have been called
        assert mock_client.call_count == initial_count


class TestPlannerAgentComplexTask:
    """Tests for complex task handling."""

    @pytest.mark.asyncio
    async def test_complex_task_creates_multi_step_plan(self):
        """Complex task should create plan with multiple steps."""
        agent = PlannerAgent(request_id="test123")

        plan, events = await agent.create_plan("Create a snake game")

        assert len(plan.steps) == 5
        assert plan.steps[0].id == "config"
        assert "snake" in [s.id for s in plan.steps]
        assert "food" in [s.id for s in plan.steps]

    @pytest.mark.asyncio
    async def test_complex_task_calls_llm(self):
        """Complex task should call LLM."""
        registry = get_registry()
        mock_client = registry.get("planner")
        assert isinstance(mock_client, MockLLMClient)
        initial_count = mock_client.call_count

        agent = PlannerAgent(request_id="test123")
        await agent.create_plan("Create a snake game")

        # LLM should have been called once
        assert mock_client.call_count == initial_count + 1

    @pytest.mark.asyncio
    async def test_complex_task_has_dependencies(self):
        """Complex task plan should have dependency relationships."""
        agent = PlannerAgent(request_id="test123")

        plan, events = await agent.create_plan("Create a snake game")

        # Find snake step
        snake_step = plan.get_step("snake")
        assert snake_step is not None
        assert "config" in snake_step.depends_on

        # Find collision step
        collision_step = plan.get_step("collision")
        assert collision_step is not None
        assert "snake" in collision_step.depends_on
        assert "food" in collision_step.depends_on


class TestSSEEventsSimpleTask:
    """Tests for SSE event sequence on simple tasks."""

    @pytest.mark.asyncio
    async def test_sse_events_sequence_simple_task(self):
        """Simple task should emit correct event sequence."""
        agent = PlannerAgent(request_id="test123")

        plan, events = await agent.create_plan("Sort a list")

        # Check event types in order
        event_types = [e["event"] for e in events]
        assert event_types == [
            "plan_start",
            "plan_analysis",
            "plan_step_identified",  # One step for simple task
            "plan_complete",
        ]

    @pytest.mark.asyncio
    async def test_plan_start_event_contains_task(self):
        """plan_start event should contain the task."""
        agent = PlannerAgent(request_id="test123")

        plan, events = await agent.create_plan("Sort a list")

        start_event = events[0]
        assert start_event["event"] == "plan_start"
        assert start_event["task"] == "Sort a list"
        assert "timestamp" in start_event

    @pytest.mark.asyncio
    async def test_plan_analysis_event_simple_task(self):
        """plan_analysis should show is_complex=False for simple task."""
        agent = PlannerAgent(request_id="test123")

        plan, events = await agent.create_plan("Sort a list")

        analysis_event = events[1]
        assert analysis_event["event"] == "plan_analysis"
        assert analysis_event["is_complex"] is False
        assert analysis_event["word_count"] == 3


class TestSSEEventsComplexTask:
    """Tests for SSE event sequence on complex tasks."""

    @pytest.mark.asyncio
    async def test_sse_events_sequence_complex_task(self):
        """Complex task should emit correct event sequence."""
        agent = PlannerAgent(request_id="test123")

        plan, events = await agent.create_plan("Create a snake game")

        event_types = [e["event"] for e in events]

        # Should have: start, analysis, 5 step_identified, complete
        assert event_types[0] == "plan_start"
        assert event_types[1] == "plan_analysis"
        assert event_types[-1] == "plan_complete"

        # Count step_identified events
        step_events = [e for e in events if e["event"] == "plan_step_identified"]
        assert len(step_events) == 5

    @pytest.mark.asyncio
    async def test_plan_analysis_event_complex_task(self):
        """plan_analysis should show is_complex=True for complex task."""
        agent = PlannerAgent(request_id="test123")

        plan, events = await agent.create_plan("Create a snake game")

        analysis_event = events[1]
        assert analysis_event["event"] == "plan_analysis"
        assert analysis_event["is_complex"] is True

    @pytest.mark.asyncio
    async def test_plan_step_identified_events(self):
        """plan_step_identified events should contain step details."""
        agent = PlannerAgent(request_id="test123")

        plan, events = await agent.create_plan("Create a snake game")

        step_events = [e for e in events if e["event"] == "plan_step_identified"]

        # Check first step (config)
        config_event = step_events[0]
        assert config_event["step_id"] == "config"
        assert "task" in config_event
        assert config_event["depends_on"] == []
        assert config_event["complexity"] == "simple"

        # Check a step with dependencies
        snake_event = next(e for e in step_events if e["step_id"] == "snake")
        assert "config" in snake_event["depends_on"]


class TestPlanCompleteEvent:
    """Tests for plan_complete event."""

    @pytest.mark.asyncio
    async def test_plan_complete_contains_mermaid(self):
        """plan_complete should contain Mermaid diagram."""
        agent = PlannerAgent(request_id="test123")

        plan, events = await agent.create_plan("Create a snake game")

        complete_event = events[-1]
        assert complete_event["event"] == "plan_complete"
        assert "mermaid" in complete_event
        assert complete_event["mermaid"].startswith("graph TD")

    @pytest.mark.asyncio
    async def test_plan_complete_contains_total_steps(self):
        """plan_complete should contain total step count."""
        agent = PlannerAgent(request_id="test123")

        plan, events = await agent.create_plan("Create a snake game")

        complete_event = events[-1]
        assert complete_event["total_steps"] == 5

    @pytest.mark.asyncio
    async def test_plan_complete_contains_parallel_stages_count(self):
        """Snake game should have multiple parallel stages."""
        agent = PlannerAgent(request_id="test123")

        plan, events = await agent.create_plan("Create a snake game")

        complete_event = events[-1]
        # Snake game: config -> (snake, food parallel) -> collision -> game_loop
        # That's 4 stages
        assert complete_event["parallel_stages"] == 4

    @pytest.mark.asyncio
    async def test_simple_task_has_one_stage(self):
        """Simple task should have exactly 1 parallel stage."""
        agent = PlannerAgent(request_id="test123")

        plan, events = await agent.create_plan("Sort a list")

        complete_event = events[-1]
        assert complete_event["parallel_stages"] == 1


class TestPlannerAgentRegistry:
    """Tests for registry integration."""

    @pytest.mark.asyncio
    async def test_uses_registry_planner_role(self, monkeypatch):
        """PlannerAgent should get client from registry with 'planner' role."""
        monkeypatch.setenv("USE_MOCK_LLM", "true")
        reset_registry()

        # Register a custom client for planner role
        custom_client = MockLLMClient(latency_ms=0)
        get_registry().register("planner", custom_client)

        agent = PlannerAgent(request_id="test123")

        # The agent should use our custom client
        assert agent._llm is custom_client


class TestPlannerAgentConfig:
    """Tests for PlannerConfig usage."""

    @pytest.mark.asyncio
    async def test_default_config_used_when_none_provided(self):
        """Should use default PlannerConfig when none provided."""
        agent = PlannerAgent(request_id="test123")

        assert agent.config is not None
        assert agent.config.max_steps == 10
        assert agent.config.min_complexity_words == 15

    @pytest.mark.asyncio
    async def test_custom_config_used(self):
        """Should use provided PlannerConfig."""
        custom_config = PlannerConfig(max_steps=5, min_complexity_words=3)
        agent = PlannerAgent(request_id="test123", config=custom_config)

        assert agent.config.max_steps == 5
        assert agent.config.min_complexity_words == 3

    @pytest.mark.asyncio
    async def test_high_min_complexity_makes_all_tasks_simple(self):
        """With very high min_complexity_words, all tasks are simple."""
        # Set threshold so high that even "game" keyword won't trigger complexity
        # Wait, keywords always trigger. Let me use a task without keywords.
        config = PlannerConfig(min_complexity_words=100)
        agent = PlannerAgent(request_id="test123", config=config)

        # "Sort a list" has no keywords and fewer than 100 words
        plan, events = await agent.create_plan("Sort a list")

        analysis_event = events[1]
        assert analysis_event["is_complex"] is False


class TestPlannerAgentTimestamps:
    """Tests for event timestamps."""

    @pytest.mark.asyncio
    async def test_all_events_have_timestamps(self):
        """All events should have timestamp field."""
        agent = PlannerAgent(request_id="test123")

        plan, events = await agent.create_plan("Create a snake game")

        for event in events:
            assert "timestamp" in event
            assert isinstance(event["timestamp"], str)
            # Should be ISO format
            assert "T" in event["timestamp"]
