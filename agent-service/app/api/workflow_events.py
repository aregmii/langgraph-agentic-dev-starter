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
    NODE_START = "node_start"
    NODE_COMPLETE = "node_complete"
    RETRY = "retry"
    ERROR = "error"
    RESULT = "result"
    # Planner agent events
    PLAN_START = "plan_start"
    PLAN_ANALYSIS = "plan_analysis"
    PLAN_STEP_IDENTIFIED = "plan_step_identified"
    PLAN_COMPLETE = "plan_complete"

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