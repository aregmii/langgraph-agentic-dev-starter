"""
Task State Definition

This module defines the state of a task as it flows through
the LangGraph agent workflow. Each node receives state,
performs work, and returns updated state.

Extension point: Additional fields can be added here to track additional info as it flows through the workflow.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime


class TaskType(str, Enum):
    """
    Supported task types.
    
    Extension point: Add new task types here when extending
    the agent's capabilities.
    """
    CODE_GENERATION = "code_generation"
    CODE_FIX = "code_fix"
    CODE_REFACTOR = "code_refactor"
    CODE_TESTING = "code_testing"
    CODE_REVIEW = "code_review"


class TaskStatus(str, Enum):
    """
    Task lifecycle status.
    
    Updated when ENTERING a stage. Terminal states are
    COMPLETED and FAILED.
    """
    PENDING = "pending"           # Created, not yet started
    IN_ROUTING = "in_routing"     # Being routed to appropriate handler
    IN_EXECUTION = "in_execution" # Code being generated/modified
    IN_EVALUATION = "in_evaluation" # Output being evaluated
    COMPLETED = "completed"       # Successfully finished (terminal)
    FAILED = "failed"             # Failed after retries (terminal)


@dataclass
class TaskState:
    """
    State of a single task flowing through the agent workflow.
    
    Each node in the graph receives this state, performs its work,
    and returns an updated state. This design enables:
    - Full traceability of agent decisions
    - Easy serialization for async queue processing
    - Clean separation between nodes
    
    Example:
        state = TaskState(
            task_id="abc-123",
            task_type=TaskType.CODE_GENERATION,
            input_description="Write a function to sort a list"
        )
    """
    # Identity
    task_id: str
    task_type: TaskType
    
    # Input
    input_description: str
    context: Optional[str] = None  # Additional context (e.g., existing code)
    
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
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def with_updates(self, **kwargs) -> "TaskState":
        """
        Create a new state with updated fields.
        
        This maintains immutability - we never modify state in place.
        
        Example:
            new_state = state.with_updates(
                status=TaskStatus.IN_EXECUTION,
                generated_code="def sort_list(lst): ..."
            )
        """
        from dataclasses import asdict
        current = asdict(self)
        current.update(kwargs)
        current["updated_at"] = datetime.utcnow()
        return TaskState(**current)
    
    def is_retriable(self) -> bool:
        """Check if the task can be retried."""
        return self.retry_count < self.max_retries
    
    def increment_retry(self) -> "TaskState":
        """Return new state with incremented retry count."""
        return self.with_updates(retry_count=self.retry_count + 1)