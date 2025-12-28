"""
Task State Definition

State of a task as it flows through the code agent workflow.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime, timezone

class TaskType(str, Enum):
    """What kind of coding task is this?"""
    CODE_GENERATION = "code_generation"
    CODE_FIX = "code_fix"
    CODE_REFACTOR = "code_refactor"
    CODE_TESTING = "code_testing"
    CODE_REVIEW = "code_review"


class TaskStatus(str, Enum):
    """Current step in the workflow."""
    PENDING = "pending"           # Created, not yet started
    IDENTIFYING = "identifying"   # Determining task type
    EXECUTING = "executing"       # LLM generating code
    EVALUATING = "evaluating"     # Checking output quality
    RETRYING = "retrying"         # Failed, attempting again
    COMPLETED = "completed"       # Success (terminal)
    FAILED = "failed"             # Failed permanently (terminal)


@dataclass
class TaskState:
    """State of a single task flowing through the workflow."""
    
    # Identity
    task_id: str
    task_type: TaskType
    
    # Input
    input_description: str
    context: Optional[str] = None
    
    # Output
    generated_code: Optional[str] = None
    test_results: Optional[dict] = None
    
    # Evaluation
    evaluation_score: Optional[float] = None
    evaluation_feedback: Optional[str] = None
    
    # Workflow control
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    
    # Error handling
    error_message: Optional[str] = None
    
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def with_updates(self, **kwargs) -> "TaskState":
        """Create a new state with updated fields."""
        from dataclasses import asdict
        current = asdict(self)
        current.update(kwargs)
        current["updated_at"] = datetime.now(timezone.utc)  # Updated timestamp
        return TaskState(**current)
    
    def is_retriable(self) -> bool:
        """Check if the task can be retried."""
        return self.retry_count < self.max_retries
    
    def increment_retry(self) -> "TaskState":
        """Return new state with incremented retry count."""
        return self.with_updates(
            retry_count=self.retry_count + 1,
            status=TaskStatus.RETRYING
        )