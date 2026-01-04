"""
Data structures for the Planner Agent.

The Planner Agent breaks complex tasks into executable steps with dependencies,
enabling parallel execution where possible and sequential execution where required.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PlanStep:
    """
    Represents a single step in an execution plan.

    Each step has a unique identifier, a task description, and optionally
    depends on other steps that must complete before it can run.

    Attributes:
        id: Unique identifier for this step (e.g., "snake", "config").
            Used for dependency references and tracking.
        task: Human-readable description of what code to generate
            (e.g., "Create Snake class with movement logic").
        depends_on: List of step IDs that must complete before this step
            can begin execution. Empty list means no dependencies.
        complexity: Estimated complexity level affecting generation strategy.
            One of: "simple", "medium", "complex".
        status: Current execution status of this step.
            One of: "pending", "in_progress", "completed", "failed".

    Example:
        >>> step = PlanStep(
        ...     id="snake",
        ...     task="Create Snake class with position and movement",
        ...     depends_on=["config"],
        ...     complexity="medium"
        ... )
    """

    id: str
    task: str
    depends_on: list[str] = field(default_factory=list)
    complexity: str = "medium"
    status: str = "pending"

    def __post_init__(self) -> None:
        """Validate field values after initialization."""
        valid_complexities = {"simple", "medium", "complex"}
        if self.complexity not in valid_complexities:
            raise ValueError(
                f"complexity must be one of {valid_complexities}, got '{self.complexity}'"
            )

        valid_statuses = {"pending", "in_progress", "completed", "failed"}
        if self.status not in valid_statuses:
            raise ValueError(
                f"status must be one of {valid_statuses}, got '{self.status}'"
            )


@dataclass
class ProjectPlan:
    """
    Represents a complete execution plan for a project.

    A ProjectPlan contains the original user request, the LLM's reasoning
    for how it decomposed the task, and the ordered list of steps to execute.

    Attributes:
        original_task: The original task description from the user
            (e.g., "Create a snake game").
        reasoning: LLM's explanation for why it broke down the task this way,
            useful for debugging and user understanding.
        steps: List of all PlanStep objects in the plan.

    Example:
        >>> plan = ProjectPlan(
        ...     original_task="Create a snake game",
        ...     reasoning="Breaking into config, entities, and game loop",
        ...     steps=[
        ...         PlanStep(id="config", task="Game constants"),
        ...         PlanStep(id="snake", task="Snake class", depends_on=["config"]),
        ...     ]
        ... )
        >>> stages = plan.get_execution_stages()
        >>> print(plan.to_mermaid())
    """

    original_task: str
    reasoning: str
    steps: list[PlanStep] = field(default_factory=list)

    def get_execution_stages(self) -> list[list[PlanStep]]:
        """
        Compute execution order based on dependencies.

        Uses a topological sort variant (Kahn's algorithm) to group steps
        into stages where all steps in a stage can run in parallel.

        Returns:
            List of stages, where each stage is a list of PlanStep objects
            that can execute concurrently. Stages must execute sequentially.

            - Stage 0: Steps with no dependencies (run in parallel)
            - Stage 1: Steps whose deps are all in Stage 0 (run in parallel)
            - Stage N: Steps whose deps are all in Stages 0 to N-1

        Raises:
            ValueError: If circular dependencies are detected.

        Example:
            >>> plan = ProjectPlan(
            ...     original_task="Snake game",
            ...     reasoning="...",
            ...     steps=[
            ...         PlanStep(id="config", task="Config", depends_on=[]),
            ...         PlanStep(id="snake", task="Snake", depends_on=["config"]),
            ...         PlanStep(id="food", task="Food", depends_on=["config"]),
            ...         PlanStep(id="game", task="Game loop", depends_on=["snake", "food"]),
            ...     ]
            ... )
            >>> stages = plan.get_execution_stages()
            >>> len(stages)
            3
            >>> [s.id for s in stages[0]]
            ['config']
            >>> [s.id for s in stages[1]]  # snake and food can run in parallel
            ['snake', 'food']
            >>> [s.id for s in stages[2]]
            ['game']
        """
        if not self.steps:
            return []

        # Build a map of step_id -> step for quick lookup
        step_map: dict[str, PlanStep] = {step.id: step for step in self.steps}

        # Track which steps have been assigned to a stage
        staged_ids: set[str] = set()

        # Build initial dependency sets for each step
        remaining_deps: dict[str, set[str]] = {
            step.id: set(step.depends_on) for step in self.steps
        }

        stages: list[list[PlanStep]] = []

        while len(staged_ids) < len(self.steps):
            # Find all steps whose dependencies are satisfied
            ready_ids: list[str] = [
                step_id
                for step_id, deps in remaining_deps.items()
                if step_id not in staged_ids and deps.issubset(staged_ids)
            ]

            if not ready_ids:
                # No progress possible - circular dependency detected
                unstaged = set(step_map.keys()) - staged_ids
                raise ValueError(
                    f"Circular dependency detected. Unable to stage: {unstaged}"
                )

            # Create this stage with all ready steps
            stage = [step_map[step_id] for step_id in ready_ids]
            stages.append(stage)

            # Mark these steps as staged
            staged_ids.update(ready_ids)

        return stages

    def to_mermaid(self) -> str:
        """
        Generate a Mermaid diagram string representing the plan.

        Creates a top-down flowchart showing each step as a node and
        arrows indicating dependencies between steps.

        Returns:
            Mermaid diagram string that can be rendered by Mermaid.js.

        Example:
            >>> plan = ProjectPlan(
            ...     original_task="Snake game",
            ...     reasoning="...",
            ...     steps=[
            ...         PlanStep(id="config", task="Game Config", depends_on=[]),
            ...         PlanStep(id="snake", task="Snake Class", depends_on=["config"]),
            ...     ]
            ... )
            >>> print(plan.to_mermaid())
            graph TD
                config[Game Config]
                snake[Snake Class]
                config --> snake
        """
        if not self.steps:
            return "graph TD\n    empty[No steps in plan]"

        lines = ["graph TD"]

        # Add all nodes first
        for step in self.steps:
            # Escape special characters for Mermaid v11+
            # Remove or replace characters that break Mermaid parsing
            safe_task = step.task
            safe_task = safe_task.replace("[", "")
            safe_task = safe_task.replace("]", "")
            safe_task = safe_task.replace("(", "")
            safe_task = safe_task.replace(")", "")
            safe_task = safe_task.replace('"', "'")
            safe_task = safe_task.replace("<", "")
            safe_task = safe_task.replace(">", "")
            # Use quoted label syntax for safety
            lines.append(f'    {step.id}["{safe_task}"]')

        # Add all dependency edges
        for step in self.steps:
            for dep_id in step.depends_on:
                lines.append(f"    {dep_id} --> {step.id}")

        return "\n".join(lines)

    def get_step(self, step_id: str) -> Optional[PlanStep]:
        """
        Find a step by its unique identifier.

        Args:
            step_id: The unique identifier of the step to find.

        Returns:
            The PlanStep with the given ID, or None if not found.

        Example:
            >>> plan = ProjectPlan(
            ...     original_task="...",
            ...     reasoning="...",
            ...     steps=[PlanStep(id="config", task="Config")]
            ... )
            >>> step = plan.get_step("config")
            >>> step.task
            'Config'
            >>> plan.get_step("nonexistent") is None
            True
        """
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def update_step_status(self, step_id: str, status: str) -> None:
        """
        Update a step's execution status.

        Args:
            step_id: The unique identifier of the step to update.
            status: New status value. Must be one of:
                "pending", "in_progress", "completed", "failed".

        Raises:
            ValueError: If step_id is not found or status is invalid.

        Example:
            >>> plan = ProjectPlan(
            ...     original_task="...",
            ...     reasoning="...",
            ...     steps=[PlanStep(id="config", task="Config")]
            ... )
            >>> plan.update_step_status("config", "in_progress")
            >>> plan.get_step("config").status
            'in_progress'
        """
        valid_statuses = {"pending", "in_progress", "completed", "failed"}
        if status not in valid_statuses:
            raise ValueError(
                f"status must be one of {valid_statuses}, got '{status}'"
            )

        step = self.get_step(step_id)
        if step is None:
            raise ValueError(f"Step with id '{step_id}' not found")

        step.status = status


@dataclass
class PlannerConfig:
    """
    Configuration options for the Planner Agent.

    Controls behavior like maximum plan complexity, when to skip planning
    for simple tasks, and timeout limits.

    Attributes:
        max_steps: Maximum number of steps allowed in a plan.
            Prevents overly complex decompositions. Default: 10.
        min_complexity_words: Minimum word count in task description
            to trigger planning. Tasks with fewer words are considered
            simple enough to execute directly. Default: 15.
        timeout_seconds: Maximum time allowed for plan generation.
            Prevents hanging on complex planning requests. Default: 30.

    Example:
        >>> config = PlannerConfig(max_steps=5, timeout_seconds=60)
        >>> # For simple tasks, skip planning entirely
        >>> task = "Print hello world"
        >>> if len(task.split()) < config.min_complexity_words:
        ...     print("Task too simple, skipping planner")
        Task too simple, skipping planner
    """

    max_steps: int = 10
    min_complexity_words: int = 15
    timeout_seconds: int = 30

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.max_steps < 1:
            raise ValueError("max_steps must be at least 1")
        if self.min_complexity_words < 0:
            raise ValueError("min_complexity_words cannot be negative")
        if self.timeout_seconds < 1:
            raise ValueError("timeout_seconds must be at least 1")
