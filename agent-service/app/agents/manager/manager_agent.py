"""Manager Agent - Orchestrates team of specialized agents.

The Manager Agent uses a FIXED workflow:
1. Builder generates code (plans + implements) - 2 LLM calls
2. Reviewer validates code (syntax + LLM review) - 1 LLM call
3. If review fails, retry with Builder (reflection loop) - 1 LLM call per retry
4. DocGen adds documentation - 1 LLM call
5. Assemble final result

This is the main entry point for multi-agent task execution.
"""

import time
from typing import Callable

from app.core.base_llm import BaseLLMClient
from app.models.agents import AgentType, AgentTeam
from app.models.execution import (
    StepTask, CodeOutput, CompletedStep,
    DocumentedCode, ProjectResult,
)
from app.agents.builder import SoftwareBuilderAgent
from app.agents.reviewer import SoftwareReviewerAgent
from app.agents.docgen import DocumentationGeneratorAgent


class ManagerAgent:
    """Orchestrates a team of agents to complete software tasks.

    Fixed workflow:
    1. Builder: plans implementation → generates code (2 LLM calls)
    2. Reviewer: syntax check → LLM code review (1 LLM call)
    3. If failed: retry with Builder using reflection (1 LLM call)
    4. DocGen: add documentation (1 LLM call)
    5. Assemble and return result
    """

    MAX_RETRY_ATTEMPTS = 3  # Max Builder→Reviewer cycles (1 initial + 2 retries)
    ENABLE_DOCGEN = True  # Enable documentation generation

    def __init__(
        self,
        llm_client: BaseLLMClient,
        team: AgentTeam | None = None,
        event_callback: Callable[[str, dict], None] | None = None,
    ):
        self.llm_client = llm_client
        self.event_callback = event_callback or (lambda e, d: None)

        # Create default team if not provided
        if team is None:
            self.team = AgentTeam()
            self.team.add_agent(SoftwareBuilderAgent(
                llm_client=llm_client,
                agent_id="builder-1",
                event_callback=self.event_callback,
            ))
            self.team.add_agent(SoftwareReviewerAgent(
                llm_client=llm_client,  # Now uses LLM for code review
                agent_id="reviewer-1",
                event_callback=self.event_callback,
            ))
            if self.ENABLE_DOCGEN:
                self.team.add_agent(DocumentationGeneratorAgent(
                    llm_client=llm_client,
                    agent_id="docgen-1",
                    event_callback=self.event_callback,
                ))
        else:
            self.team = team

    def _emit(self, event: str, data: dict) -> None:
        """Emit an SSE event."""
        self.event_callback(event, data)

    def _get_plan_steps(self) -> list[str]:
        """Get the Manager's plan as a list of steps."""
        steps = []
        if self.team.builders:
            steps.append("Use SoftwareBuilderAgent to generate code")
        if self.team.reviewers:
            steps.append(f"Use SoftwareReviewerAgent to review code (up to {self.MAX_RETRY_ATTEMPTS} attempts)")
        if self.team.docgens:
            steps.append("Use DocumentationGeneratorAgent to add documentation")
        return steps

    async def run(self, task: str) -> ProjectResult:
        """Execute the complete workflow for a task.

        This is the main entry point. The workflow is fixed:
        Builder → Reviewer (with retries) → DocGen → Assemble
        """
        start_time = time.time()

        # Get plan steps
        plan_steps = self._get_plan_steps()

        # STEP 1: Manager receives task and shows plan
        self._emit("manager_received_task", {"task": task})
        self._emit("manager_plan", {
            "steps": plan_steps,
            "team_summary": self.team.get_team_summary(),
        })

        # STEP 2: Execute Builder → Reviewer loop
        builder = self.team.get_agent(AgentType.BUILDER)
        reviewer = self.team.get_agent(AgentType.REVIEWER)

        if not builder:
            raise RuntimeError("No builder agent in team")

        attempt = 0
        issues = []
        code_output = None
        previous_code = ""
        workflow_passed = False

        while attempt < self.MAX_RETRY_ATTEMPTS:
            attempt += 1

            # Delegate to Builder
            action = "generate code" if attempt == 1 else f"fix code (attempt {attempt}/{self.MAX_RETRY_ATTEMPTS})"
            self._emit("manager_delegating", {
                "agent": "SoftwareBuilderAgent",
                "agent_id": builder.agent_id,
                "action": action,
            })

            step_task = StepTask(
                step_id="main",
                task=task,
                project_goal=task,
                completed_code={},
                issues=issues,
                previous_code=previous_code,  # For reflection
            )

            code_output = await builder.execute(step_task)
            previous_code = code_output.code  # Save for next iteration

            # Delegate to Reviewer (if available)
            if reviewer:
                self._emit("manager_delegating", {
                    "agent": "SoftwareReviewerAgent",
                    "agent_id": reviewer.agent_id,
                    "action": "review code",
                })

                review_result = await reviewer.execute(code_output, task)

                if review_result.overall_passed:
                    workflow_passed = True
                    break

                # Prepare for retry
                issues = review_result.issues
                blocking_count = len([i for i in issues if i.severity == "error"])

                if attempt < self.MAX_RETRY_ATTEMPTS:
                    self._emit("reflection_start", {
                        "attempt": attempt,
                        "max_attempts": self.MAX_RETRY_ATTEMPTS,
                        "blocking_issues": blocking_count,
                        "issues": [i.message for i in issues if i.severity == "error"][:3],
                    })
            else:
                workflow_passed = True
                break

        # STEP 3: Documentation
        docgen = self.team.get_agent(AgentType.DOCGEN)
        if docgen and code_output and workflow_passed:
            self._emit("manager_delegating", {
                "agent": "DocumentationGeneratorAgent",
                "agent_id": docgen.agent_id,
                "action": "add documentation",
            })

            completed = CompletedStep(
                step_id="main",
                code=code_output.code,
                tests=code_output.tests,
                attempts=attempt,
                passed=workflow_passed,
            )
            documented = await docgen.execute([completed], task)
            self._emit("docgen_complete", {
                "agent_id": docgen.agent_id,
                "readme_lines": documented.readme_lines,
            })
        else:
            documented = DocumentedCode(
                code=code_output.code if code_output else "",
                readme="# Project\n\nGenerated code.",
            )

        # STEP 4: Assemble result
        duration_ms = int((time.time() - start_time) * 1000)

        # Determine success based on workflow outcome
        success = workflow_passed
        error_message = None
        if not success:
            error_count = len([i for i in issues if i.severity == "error"])
            error_message = f"Review failed with {error_count} blocking issue(s) after {attempt} attempt(s)"

        result = ProjectResult(
            code=documented.code,
            tests=code_output.tests if code_output else "",
            readme=documented.readme,
            total_steps=1,
            total_attempts=attempt,
            duration_ms=duration_ms,
            success=success,
            error_message=error_message,
        )

        self._emit("manager_complete", {
            "success": success,
            "total_attempts": attempt,
            "duration_ms": duration_ms,
            "error_message": error_message,
        })

        return result


__all__ = ["ManagerAgent"]
