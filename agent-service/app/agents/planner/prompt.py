"""
LLM prompts and response parsing for the Planner Agent.

This module contains the system and user prompts that instruct the LLM
to decompose complex tasks into executable steps, plus utilities to
parse and validate LLM responses.
"""

import json
import re
from typing import Any

from .models import PlanStep, ProjectPlan, PlannerConfig


PLANNER_SYSTEM_PROMPT = """You are a software architect that breaks down coding tasks into executable steps.

Your role:
- Analyze tasks and decompose them into focused, independent code generation steps
- Identify dependencies between steps to enable parallel execution where possible
- Estimate complexity to help with resource allocation
- Return structured JSON that can be parsed programmatically

You always respond with valid JSON only, no markdown formatting or explanations outside the JSON."""


PLANNER_USER_PROMPT = """Analyze this task and break it into executable code generation steps.

Task: {task}

Rules:
1. Create 1-{max_steps} steps maximum
2. Each step should produce ONE focused piece of code
3. Use depends_on to show which steps must complete first
4. Steps with no shared dependencies can run in parallel
5. For simple tasks (single function/class), return just 1 step
6. Step IDs should be short, lowercase, snake_case (e.g., "game_config", "snake_class")

Complexity guide:
- "simple": Single function, <20 lines
- "medium": Single class or multiple functions, 20-100 lines
- "complex": Multiple classes or complex logic, >100 lines

Return ONLY this JSON format, no other text:
{{
  "reasoning": "Brief explanation of your breakdown strategy",
  "steps": [
    {{"id": "step_id", "task": "What code to generate", "depends_on": [], "complexity": "simple|medium|complex"}}
  ]
}}

Example for "Create a snake game":
{{
  "reasoning": "Breaking into config, entities, game logic, and main loop for modularity",
  "steps": [
    {{"id": "config", "task": "Game constants (screen size, colors, speed)", "depends_on": [], "complexity": "simple"}},
    {{"id": "snake", "task": "Snake class with body segments and movement", "depends_on": ["config"], "complexity": "medium"}},
    {{"id": "food", "task": "Food class with random spawn logic", "depends_on": ["config"], "complexity": "simple"}},
    {{"id": "collision", "task": "Collision detection for walls, self, and food", "depends_on": ["snake", "food"], "complexity": "medium"}},
    {{"id": "game_loop", "task": "Main game loop with pygame event handling", "depends_on": ["collision"], "complexity": "complex"}}
  ]
}}"""


# Keywords that suggest a task needs multi-step planning
COMPLEXITY_KEYWORDS = [
    "game",
    "application",
    "app",
    "website",
    "api",
    "server",
    "client",
    "with tests",
    "with documentation",
    "and",
    "including",
    "multiple",
    "full",
    "complete",
    "system",
    "service",
    "platform",
    "dashboard",
    "crud",
    "authentication",
    "database",
]


def parse_llm_response(response: str, original_task: str) -> ProjectPlan:
    """
    Parse LLM response into a ProjectPlan.

    Handles responses that may include markdown code blocks or raw JSON.
    Validates that all required fields are present and correctly typed.

    Args:
        response: Raw LLM response string, possibly with markdown formatting.
        original_task: The original task description from the user.

    Returns:
        ProjectPlan populated with PlanStep objects.

    Raises:
        ValueError: If response cannot be parsed or is missing required fields.

    Example:
        >>> response = '{"reasoning": "Simple task", "steps": [{"id": "main", "task": "Print hello", "depends_on": [], "complexity": "simple"}]}'
        >>> plan = parse_llm_response(response, "Print hello world")
        >>> len(plan.steps)
        1
    """
    # Extract JSON from markdown code blocks if present
    json_str = _extract_json(response)

    # Parse JSON
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in LLM response: {e}") from e

    # Validate top-level structure
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object, got {type(data).__name__}")

    if "reasoning" not in data:
        raise ValueError("Missing required field: 'reasoning'")

    if "steps" not in data:
        raise ValueError("Missing required field: 'steps'")

    if not isinstance(data["steps"], list):
        raise ValueError(f"'steps' must be a list, got {type(data['steps']).__name__}")

    if len(data["steps"]) == 0:
        raise ValueError("'steps' cannot be empty")

    # Parse steps
    steps = []
    step_ids = set()

    for i, step_data in enumerate(data["steps"]):
        step = _parse_step(step_data, i, step_ids)
        steps.append(step)
        step_ids.add(step.id)

    # Validate all dependencies reference existing steps
    for step in steps:
        for dep_id in step.depends_on:
            if dep_id not in step_ids:
                raise ValueError(
                    f"Step '{step.id}' depends on unknown step '{dep_id}'"
                )

    return ProjectPlan(
        original_task=original_task,
        reasoning=str(data["reasoning"]),
        steps=steps,
    )


def _extract_json(response: str) -> str:
    """
    Extract JSON from a response that may contain markdown code blocks.

    Handles formats like:
    - Raw JSON: {"key": "value"}
    - Markdown: ```json\n{"key": "value"}\n```
    - Markdown without language: ```\n{"key": "value"}\n```

    Args:
        response: Raw response string.

    Returns:
        Extracted JSON string.
    """
    response = response.strip()

    # Try to extract from markdown code block
    # Pattern matches ```json or ``` followed by content and closing ```
    code_block_pattern = r"```(?:json)?\s*\n?(.*?)\n?```"
    match = re.search(code_block_pattern, response, re.DOTALL)

    if match:
        return match.group(1).strip()

    # No code block found, assume raw JSON
    return response


def _parse_step(step_data: Any, index: int, existing_ids: set[str]) -> PlanStep:
    """
    Parse and validate a single step from the LLM response.

    Args:
        step_data: Raw step data from JSON.
        index: Step index for error messages.
        existing_ids: Set of already-parsed step IDs to check for duplicates.

    Returns:
        Validated PlanStep object.

    Raises:
        ValueError: If step data is invalid.
    """
    if not isinstance(step_data, dict):
        raise ValueError(f"Step {index} must be an object, got {type(step_data).__name__}")

    # Required fields
    if "id" not in step_data:
        raise ValueError(f"Step {index} missing required field: 'id'")
    if "task" not in step_data:
        raise ValueError(f"Step {index} missing required field: 'task'")

    step_id = str(step_data["id"])
    task = str(step_data["task"])

    # Check for duplicate IDs
    if step_id in existing_ids:
        raise ValueError(f"Duplicate step ID: '{step_id}'")

    # Optional fields with defaults
    depends_on = step_data.get("depends_on", [])
    if not isinstance(depends_on, list):
        raise ValueError(
            f"Step '{step_id}' depends_on must be a list, got {type(depends_on).__name__}"
        )
    depends_on = [str(d) for d in depends_on]

    complexity = str(step_data.get("complexity", "medium"))
    valid_complexities = {"simple", "medium", "complex"}
    if complexity not in valid_complexities:
        # Default to medium if LLM returns invalid complexity
        complexity = "medium"

    return PlanStep(
        id=step_id,
        task=task,
        depends_on=depends_on,
        complexity=complexity,
    )


def is_complex_task(task: str, config: PlannerConfig) -> bool:
    """
    Determine if a task needs multi-step planning.

    A task is considered complex if:
    1. It has more words than config.min_complexity_words, OR
    2. It contains complexity keywords suggesting multiple components

    Args:
        task: The task description to analyze.
        config: PlannerConfig with complexity thresholds.

    Returns:
        True if task should go through planner, False if it can be
        executed directly as a single step.

    Example:
        >>> config = PlannerConfig(min_complexity_words=15)
        >>> is_complex_task("Sort a list", config)
        False
        >>> is_complex_task("Create a snake game with scoring", config)
        True
    """
    task_lower = task.lower()

    # Check word count
    word_count = len(task.split())
    if word_count >= config.min_complexity_words:
        return True

    # Check for complexity keywords
    for keyword in COMPLEXITY_KEYWORDS:
        if keyword in task_lower:
            return True

    return False


def format_planner_prompt(task: str, config: PlannerConfig) -> str:
    """
    Format the planner user prompt with task and config values.

    Args:
        task: The task to plan.
        config: PlannerConfig with max_steps.

    Returns:
        Formatted prompt string ready to send to LLM.
    """
    return PLANNER_USER_PROMPT.format(task=task, max_steps=config.max_steps)
