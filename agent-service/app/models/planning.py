"""Planning models for execution plan creation.

This module defines models used by the Manager to plan task execution:
- PlanStep: Single step with dependencies and agent assignment
- ExecutionStage: Group of steps that run together (sequentially or in parallel)
- ExecutionPlan: Complete plan with stages pre-computed
"""

from dataclasses import dataclass, field

from .agents import AgentType


@dataclass
class PlanStep:
    """Single step in the execution plan.

    Each step has:
    - id: Unique identifier within the plan (e.g., "snake_class")
    - task: Description of what needs to be done
    - depends_on: List of step IDs that must complete first
    - agent_type: Which agent type handles this step
    - complexity: Estimated complexity for resource allocation
    """

    id: str
    task: str
    depends_on: list[str] = field(default_factory=list)
    agent_type: AgentType = AgentType.BUILDER
    complexity: str = "medium"  # "simple", "medium", "complex"

    def __post_init__(self):
        """Validate step data."""
        if not self.id:
            raise ValueError("Step id cannot be empty")
        if not self.task:
            raise ValueError("Step task cannot be empty")
        if self.complexity not in ("simple", "medium", "complex"):
            raise ValueError(f"Invalid complexity: {self.complexity}")


@dataclass
class ExecutionStage:
    """Group of steps that execute together in one stage.

    Within a stage:
    - If parallel=True: Steps run concurrently (asyncio.gather)
    - If parallel=False: Steps run sequentially

    Stages themselves always run sequentially (stage 1 before stage 2).
    """

    stage_number: int
    steps: list[PlanStep]
    parallel: bool  # True if steps within this stage can run simultaneously

    @property
    def step_ids(self) -> list[str]:
        """Get list of step IDs in this stage."""
        return [s.id for s in self.steps]

    @property
    def step_count(self) -> int:
        """Number of steps in this stage."""
        return len(self.steps)

    def __post_init__(self):
        """Validate stage data."""
        if self.stage_number < 1:
            raise ValueError("Stage number must be >= 1")
        if not self.steps:
            raise ValueError("Stage must have at least one step")


@dataclass
class ExecutionPlan:
    """Complete execution plan created by Manager.

    Stages are pre-computed based on dependencies:
    - Step A depends on nothing → Stage 1
    - Steps B, C depend only on A → Stage 2 (parallel=True)
    - Step D depends on B and C → Stage 3

    The Manager creates this plan by analyzing the task and its team.
    """

    task: str
    reasoning: str
    stages: list[ExecutionStage]
    team_summary: dict[str, int]  # From AgentTeam.get_team_summary()

    @property
    def total_steps(self) -> int:
        """Total number of steps across all stages."""
        return sum(len(stage.steps) for stage in self.stages)

    @property
    def parallelizable_steps(self) -> int:
        """Count of steps that run in parallel stages (>1 step)."""
        return sum(
            len(stage.steps)
            for stage in self.stages
            if stage.parallel and len(stage.steps) > 1
        )

    @property
    def total_stages(self) -> int:
        """Number of stages in the plan."""
        return len(self.stages)

    def get_step(self, step_id: str) -> PlanStep | None:
        """Find a step by ID."""
        for stage in self.stages:
            for step in stage.steps:
                if step.id == step_id:
                    return step
        return None

    def get_stage_for_step(self, step_id: str) -> ExecutionStage | None:
        """Find which stage contains a step."""
        for stage in self.stages:
            if step_id in stage.step_ids:
                return stage
        return None

    def to_mermaid(self) -> str:
        """Generate Mermaid diagram showing execution flow.

        Shows:
        - Each step as a node
        - Dependencies as arrows
        - Parallel stages highlighted
        """
        lines = ["graph TD"]

        # Add all nodes with descriptive labels
        for stage in self.stages:
            for step in stage.steps:
                # Sanitize task for mermaid (remove special chars)
                safe_task = step.task.replace('"', "'").replace("[", "(").replace("]", ")")
                lines.append(f'    {step.id}["{safe_task}"]')

        # Add edges based on dependencies
        for stage in self.stages:
            for step in stage.steps:
                for dep in step.depends_on:
                    lines.append(f"    {dep} --> {step.id}")

        # Add visual grouping for parallel stages
        for stage in self.stages:
            if stage.parallel and len(stage.steps) > 1:
                step_list = ", ".join(stage.step_ids)
                lines.append(f"    %% Stage {stage.stage_number} (parallel): {step_list}")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Convert plan to dictionary for SSE serialization."""
        return {
            "task": self.task,
            "reasoning": self.reasoning,
            "total_steps": self.total_steps,
            "total_stages": self.total_stages,
            "parallelizable_steps": self.parallelizable_steps,
            "team_summary": self.team_summary,
            "stages": [
                {
                    "stage_number": stage.stage_number,
                    "parallel": stage.parallel,
                    "steps": [
                        {
                            "id": step.id,
                            "task": step.task,
                            "depends_on": step.depends_on,
                            "agent_type": step.agent_type.value,
                            "complexity": step.complexity,
                        }
                        for step in stage.steps
                    ],
                }
                for stage in self.stages
            ],
            "mermaid": self.to_mermaid(),
        }
