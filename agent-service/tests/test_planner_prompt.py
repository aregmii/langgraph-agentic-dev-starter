"""Tests for Planner Agent prompt and parsing utilities."""

import json
import pytest

from app.agents.planner import (
    PlannerConfig,
    parse_llm_response,
    is_complex_task,
    format_planner_prompt,
    get_mock_plan_response,
    get_mock_plan_response_with_markdown,
)


class TestParseLlmResponse:
    """Tests for parse_llm_response function."""

    def test_parse_valid_json(self):
        """Parse valid JSON response without markdown."""
        response = json.dumps({
            "reasoning": "Simple task",
            "steps": [
                {"id": "main", "task": "Print hello", "depends_on": [], "complexity": "simple"}
            ]
        })

        plan = parse_llm_response(response, "Print hello world")

        assert plan.original_task == "Print hello world"
        assert plan.reasoning == "Simple task"
        assert len(plan.steps) == 1
        assert plan.steps[0].id == "main"
        assert plan.steps[0].task == "Print hello"
        assert plan.steps[0].depends_on == []
        assert plan.steps[0].complexity == "simple"
        assert plan.steps[0].status == "pending"

    def test_parse_json_in_markdown_code_block(self):
        """Parse JSON wrapped in markdown code block with json language."""
        response = """```json
{
    "reasoning": "Multi-step task",
    "steps": [
        {"id": "step1", "task": "First step", "depends_on": [], "complexity": "simple"},
        {"id": "step2", "task": "Second step", "depends_on": ["step1"], "complexity": "medium"}
    ]
}
```"""

        plan = parse_llm_response(response, "Test task")

        assert len(plan.steps) == 2
        assert plan.steps[1].depends_on == ["step1"]

    def test_parse_json_in_markdown_without_language(self):
        """Parse JSON wrapped in markdown code block without language specifier."""
        response = """```
{
    "reasoning": "Test",
    "steps": [{"id": "main", "task": "Do it", "depends_on": [], "complexity": "medium"}]
}
```"""

        plan = parse_llm_response(response, "Test")

        assert len(plan.steps) == 1
        assert plan.steps[0].id == "main"

    def test_parse_multi_step_with_dependencies(self):
        """Parse multi-step plan and verify dependencies are preserved."""
        response = json.dumps({
            "reasoning": "Snake game breakdown",
            "steps": [
                {"id": "config", "task": "Config", "depends_on": [], "complexity": "simple"},
                {"id": "snake", "task": "Snake class", "depends_on": ["config"], "complexity": "medium"},
                {"id": "food", "task": "Food class", "depends_on": ["config"], "complexity": "simple"},
                {"id": "game", "task": "Game loop", "depends_on": ["snake", "food"], "complexity": "complex"},
            ]
        })

        plan = parse_llm_response(response, "Create snake game")

        assert len(plan.steps) == 4
        assert plan.steps[3].depends_on == ["snake", "food"]

        # Verify execution stages work
        stages = plan.get_execution_stages()
        assert len(stages) == 3
        assert [s.id for s in stages[0]] == ["config"]
        assert set(s.id for s in stages[1]) == {"snake", "food"}
        assert [s.id for s in stages[2]] == ["game"]

    def test_parse_invalid_json_raises_error(self):
        """Invalid JSON should raise ValueError."""
        response = "This is not JSON at all"

        with pytest.raises(ValueError) as exc_info:
            parse_llm_response(response, "Test")

        assert "Invalid JSON" in str(exc_info.value)

    def test_parse_missing_reasoning_raises_error(self):
        """Missing reasoning field should raise ValueError."""
        response = json.dumps({
            "steps": [{"id": "main", "task": "Test", "depends_on": []}]
        })

        with pytest.raises(ValueError) as exc_info:
            parse_llm_response(response, "Test")

        assert "reasoning" in str(exc_info.value)

    def test_parse_missing_steps_raises_error(self):
        """Missing steps field should raise ValueError."""
        response = json.dumps({
            "reasoning": "Test reasoning"
        })

        with pytest.raises(ValueError) as exc_info:
            parse_llm_response(response, "Test")

        assert "steps" in str(exc_info.value)

    def test_parse_empty_steps_raises_error(self):
        """Empty steps list should raise ValueError."""
        response = json.dumps({
            "reasoning": "Test",
            "steps": []
        })

        with pytest.raises(ValueError) as exc_info:
            parse_llm_response(response, "Test")

        assert "empty" in str(exc_info.value).lower()

    def test_parse_step_missing_id_raises_error(self):
        """Step without id should raise ValueError."""
        response = json.dumps({
            "reasoning": "Test",
            "steps": [{"task": "Test", "depends_on": []}]
        })

        with pytest.raises(ValueError) as exc_info:
            parse_llm_response(response, "Test")

        assert "id" in str(exc_info.value)

    def test_parse_step_missing_task_raises_error(self):
        """Step without task should raise ValueError."""
        response = json.dumps({
            "reasoning": "Test",
            "steps": [{"id": "main", "depends_on": []}]
        })

        with pytest.raises(ValueError) as exc_info:
            parse_llm_response(response, "Test")

        assert "task" in str(exc_info.value)

    def test_parse_duplicate_step_ids_raises_error(self):
        """Duplicate step IDs should raise ValueError."""
        response = json.dumps({
            "reasoning": "Test",
            "steps": [
                {"id": "main", "task": "First", "depends_on": []},
                {"id": "main", "task": "Second", "depends_on": []},
            ]
        })

        with pytest.raises(ValueError) as exc_info:
            parse_llm_response(response, "Test")

        assert "Duplicate" in str(exc_info.value)

    def test_parse_unknown_dependency_raises_error(self):
        """Dependency on non-existent step should raise ValueError."""
        response = json.dumps({
            "reasoning": "Test",
            "steps": [
                {"id": "main", "task": "Main step", "depends_on": ["nonexistent"]}
            ]
        })

        with pytest.raises(ValueError) as exc_info:
            parse_llm_response(response, "Test")

        assert "unknown step" in str(exc_info.value).lower()

    def test_parse_defaults_complexity_to_medium(self):
        """Missing complexity should default to medium."""
        response = json.dumps({
            "reasoning": "Test",
            "steps": [{"id": "main", "task": "Test", "depends_on": []}]
        })

        plan = parse_llm_response(response, "Test")

        assert plan.steps[0].complexity == "medium"

    def test_parse_invalid_complexity_defaults_to_medium(self):
        """Invalid complexity value should default to medium."""
        response = json.dumps({
            "reasoning": "Test",
            "steps": [{"id": "main", "task": "Test", "depends_on": [], "complexity": "invalid"}]
        })

        plan = parse_llm_response(response, "Test")

        assert plan.steps[0].complexity == "medium"

    def test_parse_defaults_depends_on_to_empty(self):
        """Missing depends_on should default to empty list."""
        response = json.dumps({
            "reasoning": "Test",
            "steps": [{"id": "main", "task": "Test"}]
        })

        plan = parse_llm_response(response, "Test")

        assert plan.steps[0].depends_on == []


class TestIsComplexTask:
    """Tests for is_complex_task function."""

    def test_simple_task_by_word_count(self):
        """Short tasks without keywords are not complex."""
        config = PlannerConfig(min_complexity_words=15)

        assert is_complex_task("Sort a list", config) is False
        assert is_complex_task("Print hello world", config) is False
        assert is_complex_task("Add two numbers", config) is False

    def test_complex_task_by_word_count(self):
        """Tasks with many words are complex."""
        config = PlannerConfig(min_complexity_words=5)

        long_task = "Create a function that takes a list of numbers and returns the sorted version"
        assert is_complex_task(long_task, config) is True

    def test_complex_task_by_keyword_game(self):
        """Tasks with 'game' keyword are complex."""
        config = PlannerConfig(min_complexity_words=100)  # High threshold

        assert is_complex_task("Create a snake game", config) is True
        assert is_complex_task("Build a game", config) is True

    def test_complex_task_by_keyword_application(self):
        """Tasks with 'application' keyword are complex."""
        config = PlannerConfig(min_complexity_words=100)

        assert is_complex_task("Build an application", config) is True
        assert is_complex_task("Create a web app", config) is True

    def test_complex_task_by_keyword_and(self):
        """Tasks with 'and' keyword (multiple components) are complex."""
        config = PlannerConfig(min_complexity_words=100)

        assert is_complex_task("Create login and signup", config) is True

    def test_complex_task_by_keyword_api(self):
        """Tasks with 'api' keyword are complex."""
        config = PlannerConfig(min_complexity_words=100)

        assert is_complex_task("Build a REST API", config) is True

    def test_complex_task_by_keyword_with_tests(self):
        """Tasks with 'with tests' are complex."""
        config = PlannerConfig(min_complexity_words=100)

        assert is_complex_task("Create function with tests", config) is True

    def test_keywords_case_insensitive(self):
        """Keyword matching should be case insensitive."""
        config = PlannerConfig(min_complexity_words=100)

        assert is_complex_task("Create a GAME", config) is True
        assert is_complex_task("Build an APPLICATION", config) is True
        assert is_complex_task("REST API endpoint", config) is True


class TestFormatPlannerPrompt:
    """Tests for format_planner_prompt function."""

    def test_format_includes_task(self):
        """Formatted prompt should include the task."""
        config = PlannerConfig(max_steps=10)
        prompt = format_planner_prompt("Create a snake game", config)

        assert "Create a snake game" in prompt

    def test_format_includes_max_steps(self):
        """Formatted prompt should include max_steps from config."""
        config = PlannerConfig(max_steps=5)
        prompt = format_planner_prompt("Test task", config)

        assert "1-5 steps" in prompt


class TestMockResponses:
    """Tests for mock response generation."""

    def test_get_mock_response_snake(self):
        """Snake game should return multi-step mock."""
        response = get_mock_plan_response("Create a snake game")
        data = json.loads(response)

        assert len(data["steps"]) == 5
        assert data["steps"][0]["id"] == "config"

    def test_get_mock_response_sort(self):
        """Sort task should return single-step mock."""
        response = get_mock_plan_response("Sort a list")
        data = json.loads(response)

        assert len(data["steps"]) == 1

    def test_get_mock_response_calculator(self):
        """Calculator should return medium complexity mock."""
        response = get_mock_plan_response("Build a calculator")
        data = json.loads(response)

        assert len(data["steps"]) == 4

    def test_get_mock_response_unknown_task(self):
        """Unknown task should return fallback single-step."""
        response = get_mock_plan_response("Do something unusual")
        data = json.loads(response)

        assert len(data["steps"]) == 1
        assert data["steps"][0]["id"] == "main"

    def test_get_mock_response_with_markdown(self):
        """Markdown wrapper should work with parser."""
        response = get_mock_plan_response_with_markdown("Create a snake game")

        assert response.startswith("```json")
        assert response.endswith("```")

        # Should parse correctly
        plan = parse_llm_response(response, "Create a snake game")
        assert len(plan.steps) == 5


class TestIntegration:
    """Integration tests combining multiple components."""

    def test_mock_response_parses_to_valid_plan(self):
        """Mock responses should parse into valid ProjectPlans."""
        for task in ["snake game", "calculator", "todo app", "REST api"]:
            response = get_mock_plan_response(task)
            plan = parse_llm_response(response, task)

            # Should produce valid execution stages
            stages = plan.get_execution_stages()
            assert len(stages) >= 1

            # Should produce valid Mermaid
            mermaid = plan.to_mermaid()
            assert mermaid.startswith("graph TD")

    def test_end_to_end_snake_game(self):
        """Full end-to-end test for snake game planning."""
        task = "Create a snake game"
        config = PlannerConfig()

        # Should be detected as complex
        assert is_complex_task(task, config) is True

        # Get mock response
        response = get_mock_plan_response(task)

        # Parse into plan
        plan = parse_llm_response(response, task)

        # Verify stages
        stages = plan.get_execution_stages()
        assert len(stages) == 4  # config -> snake,food -> collision -> game_loop

        # Stage 1: config (no deps)
        assert len(stages[0]) == 1
        assert stages[0][0].id == "config"

        # Stage 2: snake and food (both depend on config, can run parallel)
        assert len(stages[1]) == 2
        stage2_ids = {s.id for s in stages[1]}
        assert stage2_ids == {"snake", "food"}

        # Stage 3: collision (depends on snake and food)
        assert len(stages[2]) == 1
        assert stages[2][0].id == "collision"

        # Stage 4: game_loop (depends on collision)
        assert len(stages[3]) == 1
        assert stages[3][0].id == "game_loop"

        # Verify Mermaid output
        mermaid = plan.to_mermaid()
        assert "config --> snake" in mermaid
        assert "config --> food" in mermaid
        assert "snake --> collision" in mermaid
        assert "food --> collision" in mermaid
        assert "collision --> game_loop" in mermaid
