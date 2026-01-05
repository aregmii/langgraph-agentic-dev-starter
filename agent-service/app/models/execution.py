"""Execution models for agent communication.

This module defines data structures passed between agents:
- StepTask: What Manager sends to Builder
- CodeOutput: What Builder produces
- ReviewResult: What Reviewer produces
- CompletedStep: Validated step ready for assembly
- DocumentedCode: What DocGen produces
- ProjectResult: Final output to user
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StepTask:
    """Task sent from Manager to Builder.

    Contains everything Builder needs to generate code:
    - step_id: Which step this is
    - task: Description of what to build
    - project_goal: Overall project context
    - completed_code: Code from previous steps (for reference)
    - issues: If this is a retry, issues to fix from Reviewer
    - previous_code: If retry, the code that was reviewed
    """

    step_id: str
    task: str
    project_goal: str
    completed_code: dict[str, str] = field(default_factory=dict)  # step_id -> code
    issues: list["ReviewIssue"] = field(default_factory=list)  # For retry attempts
    previous_code: str = ""  # For reflection: the code that was reviewed

    @property
    def is_retry(self) -> bool:
        """Check if this is a retry attempt (has issues to fix)."""
        return len(self.issues) > 0 and bool(self.previous_code)


@dataclass
class CodeOutput:
    """Output from Builder after generating code.

    Contains:
    - step_id: Which step this is for
    - code: Generated source code
    - tests: Generated test code
    """

    step_id: str
    code: str
    tests: str

    @property
    def code_lines(self) -> int:
        """Count of lines in generated code."""
        return len(self.code.strip().split("\n")) if self.code.strip() else 0

    @property
    def test_lines(self) -> int:
        """Count of lines in generated tests."""
        return len(self.tests.strip().split("\n")) if self.tests.strip() else 0


@dataclass
class ReviewIssue:
    """Single issue found by Reviewer.

    Issues can be:
    - error: Must be fixed (tests fail, syntax error)
    - warning: Should be fixed (code smell, missing edge case)
    - suggestion: Optional improvement
    """

    severity: str  # "error", "warning", "suggestion"
    category: str  # "correctness", "style", "performance", "security", etc.
    message: str
    suggestion: str | None = None

    def __post_init__(self):
        """Validate issue data."""
        if self.severity not in ("error", "warning", "suggestion"):
            raise ValueError(f"Invalid severity: {self.severity}")

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "suggestion": self.suggestion,
        }


@dataclass
class ReviewResult:
    """Output from Reviewer after reviewing code.

    Contains:
    - Test execution results
    - Code review results
    - List of issues found
    """

    step_id: str
    tests_passed: bool
    test_output: str
    review_passed: bool
    issues: list[ReviewIssue] = field(default_factory=list)

    @property
    def overall_passed(self) -> bool:
        """Check if both tests and review passed."""
        return self.tests_passed and self.review_passed

    @property
    def error_count(self) -> int:
        """Count of error-severity issues."""
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        """Count of warning-severity issues."""
        return sum(1 for i in self.issues if i.severity == "warning")

    def to_dict(self) -> dict:
        """Convert to dictionary for SSE serialization."""
        return {
            "step_id": self.step_id,
            "tests_passed": self.tests_passed,
            "test_output": self.test_output,
            "review_passed": self.review_passed,
            "overall_passed": self.overall_passed,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "issues": [i.to_dict() for i in self.issues],
        }


@dataclass
class CompletedStep:
    """A step that has completed the Builder → Reviewer loop.

    Created after Builder → Reviewer loop completes (passes OR max retries exhausted).
    """

    step_id: str
    code: str
    tests: str
    attempts: int  # How many Builder→Reviewer cycles it took
    passed: bool = True  # Whether review passed (False if max retries exhausted)

    @property
    def code_lines(self) -> int:
        """Count of lines in final code."""
        return len(self.code.strip().split("\n")) if self.code.strip() else 0


@dataclass
class DocumentedCode:
    """Output from DocGen after adding documentation.

    Contains:
    - code: Original code with docstrings added
    - readme: Generated README content
    """

    code: str
    readme: str

    @property
    def readme_lines(self) -> int:
        """Count of lines in README."""
        return len(self.readme.strip().split("\n")) if self.readme.strip() else 0


@dataclass
class ProjectResult:
    """Final output returned to user.

    Assembled by Manager from all completed steps + documentation.
    """

    code: str
    tests: str
    readme: str
    total_steps: int
    total_attempts: int  # Sum of attempts across all steps
    duration_ms: int
    success: bool
    error_message: str | None = None

    @property
    def code_lines(self) -> int:
        """Total lines of code."""
        return len(self.code.strip().split("\n")) if self.code.strip() else 0

    @property
    def test_lines(self) -> int:
        """Total lines of tests."""
        return len(self.tests.strip().split("\n")) if self.tests.strip() else 0

    def to_dict(self) -> dict:
        """Convert to dictionary for SSE serialization."""
        return {
            "code": self.code,
            "tests": self.tests,
            "readme": self.readme,
            "total_steps": self.total_steps,
            "total_attempts": self.total_attempts,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error_message": self.error_message,
            "code_lines": self.code_lines,
            "test_lines": self.test_lines,
        }
