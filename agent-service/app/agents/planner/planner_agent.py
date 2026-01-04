"""
Planner Agent for decomposing complex tasks into execution plans.

The PlannerAgent uses an LLM to analyze tasks and break them into
steps with dependencies, enabling parallel execution where possible.
"""

from datetime import datetime, timezone

from app.llm import get_registry
from app.logging_utils import log, short_id

from .models import PlanStep, ProjectPlan, PlannerConfig
from .prompt import (
    PLANNER_SYSTEM_PROMPT,
    format_planner_prompt,
    is_complex_task,
    parse_llm_response,
)


def _timestamp() -> str:
    """Get current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


class PlannerAgent:
    """
    Decomposes complex tasks into execution plans with parallel stages.

    Uses LLM to analyze task and identify:
    - Individual steps needed
    - Dependencies between steps
    - Which steps can run in parallel

    Example:
        >>> agent = PlannerAgent(request_id="abc123")
        >>> plan, events = await agent.create_plan("Create a snake game")
        >>> print(f"Plan has {len(plan.steps)} steps")
        >>> for event in events:
        ...     print(event["event"])
    """

    def __init__(
        self,
        request_id: str = "",
        config: PlannerConfig | None = None,
    ) -> None:
        """
        Initialize the PlannerAgent.

        Args:
            request_id: Request ID for logging/tracing
            config: PlannerConfig with settings like max_steps
        """
        self.request_id = request_id
        self.config = config or PlannerConfig()
        self._llm = get_registry().get("planner")
        self._rid = short_id(request_id) if request_id else "req-??????"

    def _log(self, message: str) -> None:
        """Log a message with request ID prefix."""
        if self.request_id:
            log(self.request_id, message)
        else:
            print(f"[{self._rid}] {message}", flush=True)

    async def create_plan(self, task: str) -> tuple[ProjectPlan, list[dict]]:
        """
        Create an execution plan for a task.

        Analyzes the task complexity and either:
        - Creates a simple single-step plan for trivial tasks
        - Uses LLM to decompose complex tasks into multiple steps

        Args:
            task: The task description to plan

        Returns:
            Tuple of (ProjectPlan, list of SSE event dicts)

        Example:
            >>> plan, events = await agent.create_plan("Create a snake game")
            >>> assert events[0]["event"] == "plan_start"
            >>> assert events[-1]["event"] == "plan_complete"
        """
        events: list[dict] = []

        # Event 1: Plan start
        self._log(f"Creating plan for: '{task[:50]}...'")
        events.append({
            "event": "plan_start",
            "task": task,
            "timestamp": _timestamp(),
        })

        # Analyze complexity
        word_count = len(task.split())
        is_complex = is_complex_task(task, self.config)

        self._log(f"Task complexity: {'complex' if is_complex else 'simple'} ({word_count} words)")

        # Event 2: Analysis result
        events.append({
            "event": "plan_analysis",
            "is_complex": is_complex,
            "word_count": word_count,
            "timestamp": _timestamp(),
        })

        # Create plan based on complexity
        if is_complex:
            plan = await self._create_complex_plan(task)
        else:
            plan = self._create_simple_plan(task)

        # Event 3-N: Each step identified
        for step in plan.steps:
            events.append({
                "event": "plan_step_identified",
                "step_id": step.id,
                "task": step.task,
                "depends_on": step.depends_on,
                "complexity": step.complexity,
                "timestamp": _timestamp(),
            })

        # Calculate parallel stages
        stages = plan.get_execution_stages()
        mermaid = plan.to_mermaid()

        self._log(f"Plan created: {len(plan.steps)} steps, {len(stages)} parallel stages")

        # Final event: Plan complete
        events.append({
            "event": "plan_complete",
            "total_steps": len(plan.steps),
            "parallel_stages": len(stages),
            "mermaid": mermaid,
            "timestamp": _timestamp(),
        })

        return plan, events

    def _create_simple_plan(self, task: str) -> ProjectPlan:
        """
        Create a single-step plan for simple tasks.

        Used when task doesn't need decomposition.

        Args:
            task: The simple task description

        Returns:
            ProjectPlan with a single step
        """
        self._log("Simple task - creating single-step plan")

        return ProjectPlan(
            original_task=task,
            reasoning="Simple task - single step execution",
            steps=[
                PlanStep(
                    id="main",
                    task=task,
                    depends_on=[],
                    complexity="simple",
                )
            ],
        )

    async def _create_complex_plan(self, task: str) -> ProjectPlan:
        """
        Use LLM to decompose a complex task into multiple steps.

        Args:
            task: The complex task to decompose

        Returns:
            ProjectPlan with multiple steps and dependencies
        """
        self._log("Complex task - calling LLM for decomposition")

        # Format prompt
        prompt = format_planner_prompt(task, self.config)

        # Call LLM
        response = await self._llm.generate(
            prompt=prompt,
            system_prompt=PLANNER_SYSTEM_PROMPT,
            temperature=0.3,  # Lower temperature for structured output
            max_tokens=2000,
        )

        self._log(f"LLM response received ({response.total_tokens} tokens)")

        # Parse response into ProjectPlan
        plan = parse_llm_response(response.content, task)

        self._log(f"Parsed plan: {len(plan.steps)} steps, reasoning: '{plan.reasoning[:50]}...'")

        return plan
