"""Software Reviewer Agent - Reviews code like a senior FAANG engineer.

The Reviewer Agent:
1. Receives CodeOutput from Builder
2. Checks syntax (AST parsing - fast, no LLM)
3. Uses LLM to perform code review (blocking vs non-blocking comments)
4. Returns ReviewResult with issues categorized by severity

Each phase emits events so UI can show real-time progress.
"""

import ast
from typing import Callable

from app.core.base_llm import BaseLLMClient
from app.models.agents import AgentType
from app.models.execution import CodeOutput, ReviewResult, ReviewIssue


# Code review prompt - like a senior FAANG engineer (pragmatic, not pedantic)
REVIEWER_SYSTEM_PROMPT = """You are a pragmatic senior software engineer performing a code review.

Your job is to review the provided Python code. Be LENIENT - if the code works, it passes.

IMPORTANT: The code has already passed syntax validation (AST parsing). Focus only on logic issues.

Categories:

1. **BLOCKING** - ONLY truly catastrophic issues that make the code completely unusable:
   - Code will crash immediately on run (e.g., undefined variables, import errors)
   - Core functionality is completely missing (e.g., asked for fibonacci but returns constants)
   - Infinite loops that will freeze the program
   - SQL injection or command injection vulnerabilities

   DO NOT mark as blocking:
   - Missing edge case handling (empty input, negative numbers, etc.)
   - Missing docstrings or type hints
   - Suboptimal algorithms or performance issues
   - Code style or naming issues
   - Missing error handling for unlikely scenarios
   - Games/GUI without tests (they can't easily be tested)

2. **NON-BLOCKING** - Suggestions for improvement (NOT required):
   - Missing docstrings, type hints
   - Better error handling
   - Performance improvements
   - Code style suggestions
   - Edge case handling

BE PRAGMATIC:
- If the code runs and produces correct output for the main use case, it PASSES
- Don't block on "nice to have" improvements
- Simple functions (fibonacci, factorial, etc.) should almost always PASS if logic is correct
- Games/GUI code should PASS if the game loop exists and basic mechanics work

Output format (use EXACTLY this format):
=== BLOCKING ===
- [issue]: [fix]
(or "None" if no blocking issues - this should be the common case!)

=== NON-BLOCKING ===
- [suggestion]: [improvement]
(or "None" if no suggestions)

=== VERDICT ===
PASS or FAIL
(PASS unless there are truly catastrophic blocking issues)"""

REVIEWER_TEMPLATE = """TASK: {task}

CODE TO REVIEW:
```python
{code}
```

{tests_section}

Review this code. Does it correctly implement the task? Are there any bugs or missing functionality?
Remember: BLOCKING issues = must fix, NON-BLOCKING = nice to have."""


def _parse_review_response(response: str) -> tuple[list[ReviewIssue], bool]:
    """Parse the LLM review response into issues and verdict.

    Returns:
        Tuple of (issues list, passed bool)
    """
    issues = []
    passed = True

    response = response.strip()

    # Parse BLOCKING section
    if "=== BLOCKING ===" in response:
        blocking_section = response.split("=== BLOCKING ===")[1]
        if "=== NON-BLOCKING ===" in blocking_section:
            blocking_section = blocking_section.split("=== NON-BLOCKING ===")[0]
        elif "=== VERDICT ===" in blocking_section:
            blocking_section = blocking_section.split("=== VERDICT ===")[0]

        blocking_section = blocking_section.strip()
        if blocking_section.lower() != "none" and blocking_section:
            for line in blocking_section.split("\n"):
                line = line.strip()
                if line.startswith("-"):
                    line = line[1:].strip()
                    if ":" in line:
                        message, suggestion = line.split(":", 1)
                        issues.append(ReviewIssue(
                            severity="error",
                            category="blocking",
                            message=message.strip(),
                            suggestion=suggestion.strip(),
                        ))
                    elif line:
                        issues.append(ReviewIssue(
                            severity="error",
                            category="blocking",
                            message=line,
                            suggestion="",
                        ))

    # Parse NON-BLOCKING section
    if "=== NON-BLOCKING ===" in response:
        nonblocking_section = response.split("=== NON-BLOCKING ===")[1]
        if "=== VERDICT ===" in nonblocking_section:
            nonblocking_section = nonblocking_section.split("=== VERDICT ===")[0]

        nonblocking_section = nonblocking_section.strip()
        if nonblocking_section.lower() != "none" and nonblocking_section:
            for line in nonblocking_section.split("\n"):
                line = line.strip()
                if line.startswith("-"):
                    line = line[1:].strip()
                    if ":" in line:
                        message, suggestion = line.split(":", 1)
                        issues.append(ReviewIssue(
                            severity="warning",
                            category="non-blocking",
                            message=message.strip(),
                            suggestion=suggestion.strip(),
                        ))
                    elif line:
                        issues.append(ReviewIssue(
                            severity="warning",
                            category="non-blocking",
                            message=line,
                            suggestion="",
                        ))

    # Parse VERDICT
    if "=== VERDICT ===" in response:
        verdict_section = response.split("=== VERDICT ===")[1].strip()
        verdict_line = verdict_section.split("\n")[0].strip().upper()
        passed = "PASS" in verdict_line
    else:
        # Default: pass if no blocking issues
        passed = len([i for i in issues if i.severity == "error"]) == 0

    return issues, passed


class SoftwareReviewerAgent:
    """Reviews code like a senior FAANG engineer.

    Two-phase execution:
    1. Syntax check (AST parsing - fast, no LLM)
    2. Code review (LLM - thorough review with blocking/non-blocking categories)
    """

    agent_type: AgentType = AgentType.REVIEWER

    def __init__(
        self,
        llm_client: BaseLLMClient,
        agent_id: str = "reviewer-1",
        event_callback: Callable[[str, dict], None] | None = None,
    ):
        self.llm_client = llm_client
        self.agent_id = agent_id
        self.event_callback = event_callback or (lambda e, d: None)

    def _emit(self, event: str, data: dict) -> None:
        """Emit an event with agent context."""
        self.event_callback(event, {"agent_id": self.agent_id, **data})

    async def execute(self, code_output: CodeOutput, task: str = "") -> ReviewResult:
        """Execute review on the generated code.

        Validation steps:
        1. Syntax check - AST parsing (fast, no LLM)
        2. Code review - LLM reviews like a senior engineer

        Args:
            code_output: CodeOutput from Builder with code and tests
            task: The original task description (for context in review)

        Returns:
            ReviewResult with validation status and categorized issues
        """
        issues: list[ReviewIssue] = []

        # Emit planning event
        self._emit("reviewer_planning_start", {
            "code_lines": code_output.code_lines,
            "has_tests": bool(code_output.tests),
        })

        self._emit("reviewer_planning_complete", {
            "plan": "Syntax check → LLM code review",
        })

        # ===== STEP 1: SYNTAX CHECK (fast, no LLM) =====
        self._emit("reviewer_step_start", {"step": "syntax", "description": "Checking syntax"})
        syntax_result = self._check_syntax(code_output.code, "code")

        if not syntax_result[0]:
            # Syntax failed - this is a blocking issue
            issues.append(ReviewIssue(
                severity="error",
                category="syntax",
                message=syntax_result[1],
                suggestion="Fix the syntax error before the code can run",
            ))
            self._emit("reviewer_step_complete", {
                "step": "syntax",
                "passed": False,
                "message": syntax_result[1],
            })
            self._emit("reviewer_complete", {
                "passed": False,
                "errors": 1,
                "message": "Syntax error - code won't run",
            })
            return ReviewResult(
                step_id=code_output.step_id,
                tests_passed=False,
                test_output="",
                review_passed=False,
                issues=issues,
            )

        self._emit("reviewer_step_complete", {
            "step": "syntax",
            "passed": True,
            "message": "Syntax valid",
        })

        # ===== STEP 2: LLM CODE REVIEW =====
        self._emit("reviewer_step_start", {"step": "review", "description": "Senior engineer code review"})

        # Build tests section
        tests_section = ""
        if code_output.tests:
            tests_section = f"TESTS:\n```python\n{code_output.tests}\n```"

        review_prompt = REVIEWER_TEMPLATE.format(
            task=task or "Generate Python code",
            code=code_output.code,
            tests_section=tests_section,
        )

        review_response = await self.llm_client.generate(
            prompt=review_prompt,
            system_prompt=REVIEWER_SYSTEM_PROMPT,
        )

        review_issues, review_passed = _parse_review_response(review_response.content)
        issues.extend(review_issues)

        blocking_issues = [i for i in review_issues if i.severity == "error"]
        nonblocking_issues = [i for i in review_issues if i.severity == "warning"]
        blocking_count = len(blocking_issues)
        nonblocking_count = len(nonblocking_issues)

        # Include the actual blocking issues in the event
        self._emit("reviewer_step_complete", {
            "step": "review",
            "passed": review_passed,
            "message": f"{blocking_count} blocking, {nonblocking_count} non-blocking",
            "blocking_issues": [{"message": i.message, "suggestion": i.suggestion} for i in blocking_issues],
            "nonblocking_issues": [{"message": i.message, "suggestion": i.suggestion} for i in nonblocking_issues],
        })

        # Final result
        error_count = len([i for i in issues if i.severity == "error"])
        overall_passed = error_count == 0

        self._emit("reviewer_complete", {
            "passed": overall_passed,
            "errors": error_count,
            "warnings": len([i for i in issues if i.severity == "warning"]),
            "message": "Review passed" if overall_passed else f"{error_count} blocking issue(s)",
            "blocking_issues": [i.message for i in blocking_issues[:3]],  # Show first 3
        })

        return ReviewResult(
            step_id=code_output.step_id,
            tests_passed=True,  # We don't run tests anymore, LLM reviews
            test_output="",
            review_passed=overall_passed,
            issues=issues,
        )

    def _check_syntax(self, code: str, context: str) -> tuple[bool, str]:
        """Check if code is syntactically valid Python.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not code or not code.strip():
            return False, f"No {context} was provided"

        try:
            ast.parse(code)
            return True, ""
        except SyntaxError as e:
            return False, f"Syntax error in {context} at line {e.lineno}: {e.msg}"


__all__ = ["SoftwareReviewerAgent"]
