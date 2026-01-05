"""Software Builder Agent - Generates code and tests for a task.

The Builder Agent:
1. Receives StepTask from Manager
2. Creates a PLAN for how to implement the task (1 LLM call)
3. Generates code + tests based on the plan (1 LLM call)
4. Returns CodeOutput to Manager

Each phase emits events so UI can show real-time progress.
"""

from typing import Callable

from app.core.base_llm import BaseLLMClient
from app.models.agents import AgentType
from app.models.execution import StepTask, CodeOutput


# Planning prompt - Builder creates implementation plan
PLANNER_SYSTEM_PROMPT = """You are an expert Python developer planning your implementation approach.
Given a task, create a brief implementation plan listing the key components you will build.

Output format:
1. [Component name]: Brief description
2. [Component name]: Brief description
...

Keep it concise - 2-5 items. Focus on what you'll build, not how."""

PLANNER_TEMPLATE = """TASK: {task}

Create a brief implementation plan (2-5 items) for this task.
List the key functions, classes, or components you will create."""

# Code generation prompt
BUILDER_SYSTEM_PROMPT = """You are an expert Python developer implementing code based on your plan.

Your task:
1. Generate clean, well-documented Python code
2. Generate pytest tests for your code

IMPORTANT:
- Include type hints and docstrings
- Write testable, modular code
- ALWAYS include example usage at the end that prints output (so users can verify it works)
- Use if __name__ == "__main__": block for example usage with print statements
- For games/GUI: Make sure the game loop runs and is fully functional
- DO NOT use markdown code blocks (no ```python or ```)
- Output ONLY raw Python code in the designated sections
"""

BUILDER_TEMPLATE = """TASK: {task}

YOUR IMPLEMENTATION PLAN:
{plan}

{feedback_section}

Generate the code now. Use this EXACT format (NO markdown, NO code blocks):

=== CODE ===
(raw Python code here - NO ```python blocks)

=== TESTS ===
(raw pytest code here - NO ```python blocks)
"""

# Reflection prompt - when fixing code based on reviewer feedback
REFLECTION_SYSTEM_PROMPT = """You are an expert Python developer fixing code based on code review feedback.

A senior engineer reviewed your code and found issues. You MUST fix ALL blocking issues.
Non-blocking issues are nice-to-fix but not required.

IMPORTANT:
- Fix ALL blocking issues - these are critical bugs or missing functionality
- The code must be COMPLETE and RUNNABLE after your fixes
- For games/GUI: Make sure the game loop runs and is fully functional
- DO NOT use markdown code blocks (no ```python or ```)
- Output ONLY raw Python code in the designated sections
"""

REFLECTION_TEMPLATE = """TASK: {task}

YOUR PREVIOUS CODE:
```python
{previous_code}
```

CODE REVIEW FEEDBACK:
{feedback}

Fix the issues and generate improved code. Use this EXACT format (NO markdown, NO code blocks):

=== CODE ===
(raw Python code here - NO ```python blocks)

=== TESTS ===
(raw pytest code here - NO ```python blocks)
"""


def _strip_markdown_code_blocks(text: str) -> str:
    """Remove ALL markdown code blocks from LLM response.

    Handles multiple code blocks and ensures clean Python code is returned.
    """
    import re

    # Remove ```python or ``` blocks - get content inside
    pattern = r'```(?:python)?\s*\n?(.*?)```'
    matches = re.findall(pattern, text, re.DOTALL)

    if matches:
        # If we found code blocks, join all their contents
        return "\n\n".join(m.strip() for m in matches)

    # No code blocks found - return as-is but strip any leading/trailing markdown
    text = text.strip()
    # Handle case where response starts with ```python on its own line
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line if it's just ```python or ```
        if lines[0].strip() in ("```python", "```"):
            lines = lines[1:]
        # Remove last line if it's just ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()

    return text


def _parse_builder_response(response: str) -> tuple[str, str]:
    """Parse builder response into code and tests.

    Handles multiple formats:
    1. === CODE === / === TESTS === markers
    2. Raw markdown code blocks
    3. Plain text code
    """
    code = ""
    tests = ""

    # First, always strip any outer markdown wrapper
    response = response.strip()

    if "=== CODE ===" in response and "=== TESTS ===" in response:
        parts = response.split("=== TESTS ===")
        if len(parts) == 2:
            code_part = parts[0].replace("=== CODE ===", "").strip()
            tests_part = parts[1].strip()
            code = _strip_markdown_code_blocks(code_part)
            tests = _strip_markdown_code_blocks(tests_part)
    elif "=== CODE ===" in response:
        # Only code section, no tests
        code_part = response.split("=== CODE ===")[-1].strip()
        code = _strip_markdown_code_blocks(code_part)
    else:
        # No markers - assume entire response is code
        code = _strip_markdown_code_blocks(response)

    return code, tests


class SoftwareBuilderAgent:
    """Generates code and tests for a task.

    Two-phase execution:
    1. Planning: Creates implementation plan (1 LLM call)
    2. Building: Generates code based on plan (1 LLM call)
    """

    agent_type: AgentType = AgentType.BUILDER

    def __init__(
        self,
        llm_client: BaseLLMClient,
        agent_id: str = "builder-1",
        event_callback: Callable[[str, dict], None] | None = None,
    ):
        self.llm_client = llm_client
        self.agent_id = agent_id
        self.event_callback = event_callback or (lambda e, d: None)

    def _emit(self, event: str, data: dict) -> None:
        """Emit an event with agent context."""
        self.event_callback(event, {"agent_id": self.agent_id, **data})

    async def execute(self, task: StepTask) -> CodeOutput:
        """Execute the build task: plan first, then generate code.

        If this is a retry (issues present), uses reflection mode to fix the code.
        """
        is_retry = bool(task.issues) and bool(task.previous_code)

        if is_retry:
            # ===== REFLECTION MODE: Fix code based on feedback =====
            return await self._execute_reflection(task)
        else:
            # ===== NORMAL MODE: Plan and generate =====
            return await self._execute_normal(task)

    async def _execute_normal(self, task: StepTask) -> CodeOutput:
        """Normal execution: plan first, then generate code."""

        # ===== PHASE 1: PLANNING =====
        self._emit("builder_planning_start", {"task": task.task})

        plan_prompt = PLANNER_TEMPLATE.format(task=task.task)
        plan_response = await self.llm_client.generate(
            prompt=plan_prompt,
            system_prompt=PLANNER_SYSTEM_PROMPT,
        )
        plan = plan_response.content.strip()

        self._emit("builder_planning_complete", {"plan": plan})

        # ===== PHASE 2: CODE GENERATION =====
        self._emit("builder_coding_start", {})

        code_prompt = BUILDER_TEMPLATE.format(
            task=task.task,
            plan=plan,
            feedback_section="",
        )

        code_response = await self.llm_client.generate(
            prompt=code_prompt,
            system_prompt=BUILDER_SYSTEM_PROMPT,
        )

        code, tests = _parse_builder_response(code_response.content)

        self._emit("builder_coding_complete", {"code_lines": len(code.split("\n"))})

        return CodeOutput(
            step_id=task.step_id,
            code=code,
            tests=tests,
        )

    async def _execute_reflection(self, task: StepTask) -> CodeOutput:
        """Reflection mode: fix code based on reviewer feedback."""

        # ===== PHASE 1: ACKNOWLEDGE FEEDBACK =====
        blocking = [i for i in task.issues if i.severity == "error"]
        nonblocking = [i for i in task.issues if i.severity == "warning"]

        self._emit("builder_planning_start", {"task": f"Fixing {len(blocking)} blocking issues"})

        # Build feedback section
        feedback_lines = []
        if blocking:
            feedback_lines.append("BLOCKING ISSUES (must fix):")
            for issue in blocking:
                feedback_lines.append(f"- {issue.message}")
                if issue.suggestion:
                    feedback_lines.append(f"  Fix: {issue.suggestion}")
        if nonblocking:
            feedback_lines.append("\nNON-BLOCKING ISSUES (nice to fix):")
            for issue in nonblocking:
                feedback_lines.append(f"- {issue.message}")
                if issue.suggestion:
                    feedback_lines.append(f"  Suggestion: {issue.suggestion}")

        feedback = "\n".join(feedback_lines)

        self._emit("builder_planning_complete", {
            "plan": f"Fix {len(blocking)} blocking, {len(nonblocking)} non-blocking issues",
        })

        # ===== PHASE 2: GENERATE FIXED CODE =====
        self._emit("builder_coding_start", {})

        reflection_prompt = REFLECTION_TEMPLATE.format(
            task=task.task,
            previous_code=task.previous_code,
            feedback=feedback,
        )

        code_response = await self.llm_client.generate(
            prompt=reflection_prompt,
            system_prompt=REFLECTION_SYSTEM_PROMPT,
        )

        code, tests = _parse_builder_response(code_response.content)

        self._emit("builder_coding_complete", {"code_lines": len(code.split("\n"))})

        return CodeOutput(
            step_id=task.step_id,
            code=code,
            tests=tests,
        )


__all__ = ["SoftwareBuilderAgent"]
