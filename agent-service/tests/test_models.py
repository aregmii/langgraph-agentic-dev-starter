"""Tests for Module 12 data models."""

import pytest
from app.models.agents import AgentType, AgentInfo, AgentTeam, AGENT_REGISTRY
from app.models.planning import PlanStep, ExecutionStage, ExecutionPlan
from app.models.execution import (
    StepTask,
    CodeOutput,
    ReviewIssue,
    ReviewResult,
    CompletedStep,
    DocumentedCode,
    ProjectResult,
)


# ===== Agent Models Tests =====

class TestAgentType:
    def test_agent_types_exist(self):
        assert AgentType.BUILDER.value == "builder"
        assert AgentType.REVIEWER.value == "reviewer"
        assert AgentType.DOCGEN.value == "docgen"

    def test_all_types_in_registry(self):
        for agent_type in AgentType:
            assert agent_type in AGENT_REGISTRY


class TestAgentInfo:
    def test_builder_info(self):
        info = AGENT_REGISTRY[AgentType.BUILDER]
        assert info.name == "SoftwareBuilderAgent"
        assert "code_generation" in info.capabilities

    def test_reviewer_info(self):
        info = AGENT_REGISTRY[AgentType.REVIEWER]
        assert info.name == "SoftwareReviewerAgent"
        assert "test_execution" in info.capabilities

    def test_docgen_info(self):
        info = AGENT_REGISTRY[AgentType.DOCGEN]
        assert info.name == "DocumentationGeneratorAgent"
        assert "readme_generation" in info.capabilities


class TestAgentTeam:
    def test_empty_team(self):
        team = AgentTeam()
        assert team.get_team_summary() == {"builders": 0, "reviewers": 0, "docgens": 0}
        assert team.get_available_types() == []
        assert not team.has_minimum_team()

    def test_get_agents_empty(self):
        team = AgentTeam()
        assert team.get_agents(AgentType.BUILDER) == []
        assert team.get_agent(AgentType.BUILDER) is None

    def test_team_summary(self):
        # Create mock agents (just need agent_type and agent_id attributes)
        class MockBuilder:
            agent_type = AgentType.BUILDER
            agent_id = "builder-1"

        class MockReviewer:
            agent_type = AgentType.REVIEWER
            agent_id = "reviewer-1"

        team = AgentTeam()
        team.add_agent(MockBuilder())
        team.add_agent(MockReviewer())

        summary = team.get_team_summary()
        assert summary["builders"] == 1
        assert summary["reviewers"] == 1
        assert summary["docgens"] == 0

    def test_get_available_types(self):
        class MockBuilder:
            agent_type = AgentType.BUILDER
            agent_id = "builder-1"

        team = AgentTeam()
        team.add_agent(MockBuilder())

        available = team.get_available_types()
        assert AgentType.BUILDER in available
        assert AgentType.REVIEWER not in available


# ===== Planning Models Tests =====

class TestPlanStep:
    def test_basic_step(self):
        step = PlanStep(id="config", task="Define constants")
        assert step.id == "config"
        assert step.task == "Define constants"
        assert step.depends_on == []
        assert step.agent_type == AgentType.BUILDER
        assert step.complexity == "medium"

    def test_step_with_dependencies(self):
        step = PlanStep(
            id="snake",
            task="Create Snake class",
            depends_on=["config"],
            complexity="complex"
        )
        assert step.depends_on == ["config"]
        assert step.complexity == "complex"

    def test_step_validation_empty_id(self):
        with pytest.raises(ValueError, match="Step id cannot be empty"):
            PlanStep(id="", task="Some task")

    def test_step_validation_empty_task(self):
        with pytest.raises(ValueError, match="Step task cannot be empty"):
            PlanStep(id="step1", task="")

    def test_step_validation_invalid_complexity(self):
        with pytest.raises(ValueError, match="Invalid complexity"):
            PlanStep(id="step1", task="Task", complexity="invalid")


class TestExecutionStage:
    def test_basic_stage(self):
        step1 = PlanStep(id="config", task="Define constants")
        stage = ExecutionStage(stage_number=1, steps=[step1], parallel=False)

        assert stage.stage_number == 1
        assert stage.step_count == 1
        assert stage.step_ids == ["config"]
        assert not stage.parallel

    def test_parallel_stage(self):
        step1 = PlanStep(id="snake", task="Snake class")
        step2 = PlanStep(id="food", task="Food class")
        stage = ExecutionStage(stage_number=2, steps=[step1, step2], parallel=True)

        assert stage.step_count == 2
        assert stage.step_ids == ["snake", "food"]
        assert stage.parallel

    def test_stage_validation_invalid_number(self):
        step = PlanStep(id="step1", task="Task")
        with pytest.raises(ValueError, match="Stage number must be >= 1"):
            ExecutionStage(stage_number=0, steps=[step], parallel=False)

    def test_stage_validation_empty_steps(self):
        with pytest.raises(ValueError, match="Stage must have at least one step"):
            ExecutionStage(stage_number=1, steps=[], parallel=False)


class TestExecutionPlan:
    def test_basic_plan(self):
        step1 = PlanStep(id="config", task="Define constants")
        stage1 = ExecutionStage(stage_number=1, steps=[step1], parallel=False)

        plan = ExecutionPlan(
            task="Create snake game",
            reasoning="Simple game with config and snake class",
            stages=[stage1],
            team_summary={"builders": 1, "reviewers": 1, "docgens": 1}
        )

        assert plan.task == "Create snake game"
        assert plan.total_steps == 1
        assert plan.total_stages == 1
        assert plan.parallelizable_steps == 0

    def test_plan_with_parallel_stage(self):
        step1 = PlanStep(id="config", task="Config")
        step2 = PlanStep(id="snake", task="Snake", depends_on=["config"])
        step3 = PlanStep(id="food", task="Food", depends_on=["config"])

        stage1 = ExecutionStage(stage_number=1, steps=[step1], parallel=False)
        stage2 = ExecutionStage(stage_number=2, steps=[step2, step3], parallel=True)

        plan = ExecutionPlan(
            task="Game",
            reasoning="Test",
            stages=[stage1, stage2],
            team_summary={"builders": 1, "reviewers": 1, "docgens": 1}
        )

        assert plan.total_steps == 3
        assert plan.total_stages == 2
        assert plan.parallelizable_steps == 2  # snake and food are parallel

    def test_get_step(self):
        step1 = PlanStep(id="config", task="Config")
        stage1 = ExecutionStage(stage_number=1, steps=[step1], parallel=False)

        plan = ExecutionPlan(
            task="Game",
            reasoning="Test",
            stages=[stage1],
            team_summary={}
        )

        assert plan.get_step("config") == step1
        assert plan.get_step("nonexistent") is None

    def test_to_mermaid(self):
        step1 = PlanStep(id="config", task="Define constants")
        step2 = PlanStep(id="snake", task="Snake class", depends_on=["config"])

        stage1 = ExecutionStage(stage_number=1, steps=[step1], parallel=False)
        stage2 = ExecutionStage(stage_number=2, steps=[step2], parallel=False)

        plan = ExecutionPlan(
            task="Game",
            reasoning="Test",
            stages=[stage1, stage2],
            team_summary={}
        )

        mermaid = plan.to_mermaid()
        assert "graph TD" in mermaid
        assert "config" in mermaid
        assert "snake" in mermaid
        assert "config --> snake" in mermaid

    def test_to_dict(self):
        step1 = PlanStep(id="config", task="Config")
        stage1 = ExecutionStage(stage_number=1, steps=[step1], parallel=False)

        plan = ExecutionPlan(
            task="Game",
            reasoning="Test plan",
            stages=[stage1],
            team_summary={"builders": 1, "reviewers": 1, "docgens": 0}
        )

        d = plan.to_dict()
        assert d["task"] == "Game"
        assert d["reasoning"] == "Test plan"
        assert d["total_steps"] == 1
        assert d["total_stages"] == 1
        assert "mermaid" in d


# ===== Execution Models Tests =====

class TestStepTask:
    def test_basic_task(self):
        task = StepTask(
            step_id="config",
            task="Define game constants",
            project_goal="Create snake game"
        )

        assert task.step_id == "config"
        assert not task.is_retry
        assert task.completed_code == {}

    def test_retry_task(self):
        issue = ReviewIssue(
            severity="error",
            category="correctness",
            message="Test failed"
        )
        task = StepTask(
            step_id="config",
            task="Define game constants",
            project_goal="Create snake game",
            issues=[issue]
        )

        assert task.is_retry


class TestCodeOutput:
    def test_basic_output(self):
        output = CodeOutput(
            step_id="config",
            code="SCREEN_WIDTH = 800\nSCREEN_HEIGHT = 600",
            tests="def test_constants():\n    assert SCREEN_WIDTH == 800"
        )

        assert output.step_id == "config"
        assert output.code_lines == 2
        assert output.test_lines == 2

    def test_empty_code(self):
        output = CodeOutput(step_id="empty", code="", tests="")
        assert output.code_lines == 0
        assert output.test_lines == 0


class TestReviewIssue:
    def test_basic_issue(self):
        issue = ReviewIssue(
            severity="error",
            category="correctness",
            message="Test failed: assertion error"
        )

        assert issue.severity == "error"
        assert issue.category == "correctness"
        assert issue.suggestion is None

    def test_issue_with_suggestion(self):
        issue = ReviewIssue(
            severity="warning",
            category="style",
            message="Long function",
            suggestion="Break into smaller functions"
        )

        assert issue.suggestion == "Break into smaller functions"

    def test_issue_validation(self):
        with pytest.raises(ValueError, match="Invalid severity"):
            ReviewIssue(severity="invalid", category="test", message="test")

    def test_to_dict(self):
        issue = ReviewIssue(
            severity="error",
            category="correctness",
            message="Failed"
        )
        d = issue.to_dict()
        assert d["severity"] == "error"
        assert d["category"] == "correctness"


class TestReviewResult:
    def test_passed_review(self):
        result = ReviewResult(
            step_id="config",
            tests_passed=True,
            test_output="All tests passed",
            review_passed=True,
            issues=[]
        )

        assert result.overall_passed
        assert result.error_count == 0
        assert result.warning_count == 0

    def test_failed_review(self):
        issue = ReviewIssue(severity="error", category="test", message="Failed")
        result = ReviewResult(
            step_id="config",
            tests_passed=False,
            test_output="1 test failed",
            review_passed=True,
            issues=[issue]
        )

        assert not result.overall_passed
        assert result.error_count == 1

    def test_to_dict(self):
        result = ReviewResult(
            step_id="config",
            tests_passed=True,
            test_output="OK",
            review_passed=True
        )
        d = result.to_dict()
        assert d["overall_passed"] is True
        assert "issues" in d


class TestCompletedStep:
    def test_basic_completed(self):
        step = CompletedStep(
            step_id="config",
            code="x = 1",
            tests="def test(): pass",
            attempts=1
        )

        assert step.code_lines == 1
        assert step.attempts == 1


class TestDocumentedCode:
    def test_basic_documented(self):
        doc = DocumentedCode(
            code='def hello():\n    """Say hello."""\n    pass',
            readme="# My Project\n\nDescription here."
        )

        assert doc.readme_lines == 3


class TestProjectResult:
    def test_successful_result(self):
        result = ProjectResult(
            code="def main(): pass",
            tests="def test_main(): pass",
            readme="# Project",
            total_steps=5,
            total_attempts=7,
            duration_ms=45000,
            success=True
        )

        assert result.success
        assert result.code_lines == 1
        assert result.test_lines == 1
        assert result.error_message is None

    def test_failed_result(self):
        result = ProjectResult(
            code="",
            tests="",
            readme="",
            total_steps=2,
            total_attempts=6,
            duration_ms=30000,
            success=False,
            error_message="Max retries exceeded"
        )

        assert not result.success
        assert result.error_message == "Max retries exceeded"

    def test_to_dict(self):
        result = ProjectResult(
            code="x = 1",
            tests="",
            readme="",
            total_steps=1,
            total_attempts=1,
            duration_ms=1000,
            success=True
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["code_lines"] == 1
        assert "duration_ms" in d
