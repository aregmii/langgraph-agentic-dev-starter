"""
Workflow Events for SSE Streaming

Events sent to clients showing real-time progress through the LangGraph workflow.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import json
from asyncio import Queue

class WorkflowEventType(str, Enum):
    """Types of events during workflow execution."""
    # Legacy CodeAgent events (kept for backwards compatibility)
    NODE_START = "node_start"
    NODE_COMPLETE = "node_complete"
    RETRY = "retry"
    ERROR = "error"
    RESULT = "result"

    # Legacy Planner agent events (Module 11)
    PLAN_START = "plan_start"
    PLAN_ANALYSIS = "plan_analysis"
    PLAN_STEP_IDENTIFIED = "plan_step_identified"
    PLAN_COMPLETE = "plan_complete"

    # ===== Module 12: Manager Agent Events =====

    # Manager lifecycle
    MANAGER_PLANNING_START = "manager_planning_start"
    MANAGER_PLANNING_COMPLETE = "manager_planning_complete"
    MANAGER_EXECUTION_START = "manager_execution_start"
    MANAGER_DELEGATING = "manager_delegating"
    MANAGER_ASSEMBLING = "manager_assembling"
    MANAGER_COMPLETE = "manager_complete"

    # Stage lifecycle
    STAGE_START = "stage_start"
    STAGE_COMPLETE = "stage_complete"

    # Step lifecycle
    STEP_COMPLETE = "step_complete"

    # Reflection loop (Builder → Reviewer retry)
    REFLECTION_START = "reflection_start"
    REFLECTION_COMPLETE = "reflection_complete"

    # Builder agent lifecycle
    BUILDER_PLANNING_START = "builder_planning_start"
    BUILDER_PLANNING_COMPLETE = "builder_planning_complete"
    BUILDER_CODING_START = "builder_coding_start"
    BUILDER_CODING_COMPLETE = "builder_coding_complete"
    BUILDER_COMPLETE = "builder_complete"

    # Reviewer agent lifecycle
    REVIEWER_PLANNING_START = "reviewer_planning_start"
    REVIEWER_PLANNING_COMPLETE = "reviewer_planning_complete"
    REVIEWER_VALIDATING_START = "reviewer_validating_start"
    REVIEWER_STEP_START = "reviewer_step_start"
    REVIEWER_STEP_COMPLETE = "reviewer_step_complete"
    REVIEWER_VALIDATING_COMPLETE = "reviewer_validating_complete"
    REVIEWER_COMPLETE = "reviewer_complete"

    # DocGen agent
    DOCGEN_COMPLETE = "docgen_complete"

@dataclass
class WorkflowEvent:
    """A single workflow event for SSE streaming."""
    event_type: WorkflowEventType
    data: dict
    timestamp: str = None  # Captured at creation
    
    def __post_init__(self):
        """Set timestamp when event is created."""
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()
    
    def to_sse(self) -> str:
        """Format as Server-Sent Event message."""
        json_data = json.dumps({
            "event": self.event_type.value,
            "timestamp": self.timestamp,
            **self.data
        })
        return f"data: {json_data}\n\n"
    
# ===== EVENT FACTORY FUNCTIONS =====

def node_start_event(node_name: str, message: str) -> WorkflowEvent:
    """Create a node start event."""
    return WorkflowEvent(
        event_type=WorkflowEventType.NODE_START,
        data={
            "node": node_name,
            "message": message,
        }
    )


def node_complete_event(node_name: str, message: str, duration_ms: float) -> WorkflowEvent:
    """Create a node complete event."""
    return WorkflowEvent(
        event_type=WorkflowEventType.NODE_COMPLETE,
        data={
            "node": node_name,
            "message": message,
            "duration_ms": round(duration_ms, 1),
        }
    )


def retry_event(attempt: int, max_attempts: int, reason: str) -> WorkflowEvent:
    """Create a retry event."""
    return WorkflowEvent(
        event_type=WorkflowEventType.RETRY,
        data={
            "attempt": attempt,
            "max_attempts": max_attempts,
            "reason": reason,
        }
    )


def error_event(node_name: str, error: str) -> WorkflowEvent:
    """Create an error event."""
    return WorkflowEvent(
        event_type=WorkflowEventType.ERROR,
        data={
            "node": node_name,
            "error": error,
        }
    )


def result_event(
    task_id: str,
    status: str,
    generated_code: str | None,
    error: str | None,
    total_duration_ms: float,
) -> WorkflowEvent:
    """Create a final result event with total workflow duration."""
    return WorkflowEvent(
        event_type=WorkflowEventType.RESULT,
        data={
            "task_id": task_id,
            "status": status,
            "generated_code": generated_code,
            "error": error,
            "total_duration_ms": round(total_duration_ms, 1),
        }
    )


# ===== Module 12: Manager Agent Event Factories =====

def manager_planning_start_event(task: str) -> WorkflowEvent:
    """Manager started planning phase."""
    return WorkflowEvent(
        event_type=WorkflowEventType.MANAGER_PLANNING_START,
        data={"task": task}
    )


def manager_planning_complete_event(
    total_stages: int,
    total_steps: int,
    parallelizable_steps: int,
    team_summary: dict[str, int],
    mermaid: str,
) -> WorkflowEvent:
    """Manager finished planning, ready to execute."""
    return WorkflowEvent(
        event_type=WorkflowEventType.MANAGER_PLANNING_COMPLETE,
        data={
            "total_stages": total_stages,
            "total_steps": total_steps,
            "parallelizable_steps": parallelizable_steps,
            "team_summary": team_summary,
            "mermaid": mermaid,
        }
    )


def manager_execution_start_event(total_stages: int) -> WorkflowEvent:
    """Manager started execution phase."""
    return WorkflowEvent(
        event_type=WorkflowEventType.MANAGER_EXECUTION_START,
        data={"total_stages": total_stages}
    )


def manager_delegating_event(
    step_id: str,
    agent_type: str,
    agent_id: str,
    task: str | None = None,
    action: str = "execute",  # "execute" or "fix"
    issues: list[dict] | None = None,
) -> WorkflowEvent:
    """Manager delegating work to an agent."""
    data = {
        "step_id": step_id,
        "agent_type": agent_type,
        "agent_id": agent_id,
        "action": action,
    }
    if task:
        data["task"] = task
    if issues:
        data["issues"] = issues
    return WorkflowEvent(
        event_type=WorkflowEventType.MANAGER_DELEGATING,
        data=data
    )


def manager_assembling_event() -> WorkflowEvent:
    """Manager assembling final output from all completed steps."""
    return WorkflowEvent(
        event_type=WorkflowEventType.MANAGER_ASSEMBLING,
        data={}
    )


def manager_complete_event(
    total_steps: int,
    total_attempts: int,
    duration_ms: int,
) -> WorkflowEvent:
    """Manager finished all work."""
    return WorkflowEvent(
        event_type=WorkflowEventType.MANAGER_COMPLETE,
        data={
            "total_steps": total_steps,
            "total_attempts": total_attempts,
            "duration_ms": duration_ms,
        }
    )


def stage_start_event(
    stage: int,
    steps: list[str],
    parallel: bool,
) -> WorkflowEvent:
    """Stage execution starting."""
    return WorkflowEvent(
        event_type=WorkflowEventType.STAGE_START,
        data={
            "stage": stage,
            "steps": steps,
            "parallel": parallel,
        }
    )


def stage_complete_event(stage: int, duration_ms: int) -> WorkflowEvent:
    """Stage execution completed."""
    return WorkflowEvent(
        event_type=WorkflowEventType.STAGE_COMPLETE,
        data={
            "stage": stage,
            "duration_ms": duration_ms,
        }
    )


def step_complete_event(step_id: str, attempts: int) -> WorkflowEvent:
    """Step fully completed (passed review)."""
    return WorkflowEvent(
        event_type=WorkflowEventType.STEP_COMPLETE,
        data={
            "step_id": step_id,
            "attempts": attempts,
        }
    )


def reflection_start_event(
    step_id: str,
    attempt: int,
    issues: list[dict],
) -> WorkflowEvent:
    """Starting reflection loop (retry after review failure)."""
    return WorkflowEvent(
        event_type=WorkflowEventType.REFLECTION_START,
        data={
            "step_id": step_id,
            "attempt": attempt,
            "issues": issues,
        }
    )


def reflection_complete_event(step_id: str, total_attempts: int) -> WorkflowEvent:
    """Reflection loop completed (passed after retry)."""
    return WorkflowEvent(
        event_type=WorkflowEventType.REFLECTION_COMPLETE,
        data={
            "step_id": step_id,
            "total_attempts": total_attempts,
        }
    )


def builder_complete_event(
    step_id: str,
    agent_id: str,
    code_lines: int,
    test_count: int,
) -> WorkflowEvent:
    """Builder agent finished generating code."""
    return WorkflowEvent(
        event_type=WorkflowEventType.BUILDER_COMPLETE,
        data={
            "step_id": step_id,
            "agent_id": agent_id,
            "code_lines": code_lines,
            "test_count": test_count,
        }
    )


def reviewer_complete_event(
    step_id: str,
    agent_id: str,
    tests_passed: bool,
    review_passed: bool,
    issues: list[dict] | None = None,
) -> WorkflowEvent:
    """Reviewer agent finished reviewing code."""
    return WorkflowEvent(
        event_type=WorkflowEventType.REVIEWER_COMPLETE,
        data={
            "step_id": step_id,
            "agent_id": agent_id,
            "tests_passed": tests_passed,
            "review_passed": review_passed,
            "overall_passed": tests_passed and review_passed,
            "issues": issues or [],
        }
    )


def docgen_complete_event(agent_id: str, readme_lines: int) -> WorkflowEvent:
    """DocGen agent finished generating documentation."""
    return WorkflowEvent(
        event_type=WorkflowEventType.DOCGEN_COMPLETE,
        data={
            "agent_id": agent_id,
            "readme_lines": readme_lines,
        }
    )


class EventQueue:
    """
    Queue for passing events from agent nodes to the SSE generator.
    
    Usage:
        queue = EventQueue()
        
        # In agent nodes:
        await queue.push(node_start_event("identify", "Analyzing..."))
        
        # In event generator:
        async for event in queue.events():
            yield event.to_sse()
    """
    
    def __init__(self):
        self._queue: Queue[WorkflowEvent | None] = Queue()
    
    async def push(self, event: WorkflowEvent):
        """Push an event to the queue."""
        await self._queue.put(event)
    
    async def complete(self):
        """Signal that no more events will be pushed."""
        await self._queue.put(None)
    
    async def events(self):
        """Async generator that yields events until complete."""
        while True:
            event = await self._queue.get()
            if event is None:
                break
            yield event