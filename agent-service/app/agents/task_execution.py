"""
Task Execution

Represents a running task with observable progress.
The internal queue is hidden - external code just calls progress() to get events.
"""

import time
from asyncio import Queue
from datetime import datetime, timezone
from app.core.task_state import TaskState
from app.api.workflow_events import (
    WorkflowEvent,
    node_start_event,
    node_complete_event,
    retry_event,
    error_event,
    result_event,
)


class TaskExecution:
    """A running task with observable progress."""

    def __init__(self, task_id: str, state: TaskState):
        self.task_id = task_id
        self.state = state
        self.current_node: str | None = None
        self.started_at = datetime.now(timezone.utc)
        self._events: Queue[WorkflowEvent | None] = Queue()
        self._node_start_time: float | None = None

    # === Agent calls these ===

    def start_node(self, node_name: str, message: str):
        """Called when a node begins."""
        self.current_node = node_name
        self._node_start_time = time.time()
        self._events.put_nowait(node_start_event(node_name, message))

    def complete_node(self, node_name: str, message: str):
        """Called when a node completes."""
        duration_ms = 0.0
        if self._node_start_time:
            duration_ms = (time.time() - self._node_start_time) * 1000
        self._events.put_nowait(node_complete_event(node_name, message, duration_ms))
        self.current_node = None
        self._node_start_time = None

    def retry(self, attempt: int, max_attempts: int, reason: str):
        """Called when a retry occurs."""
        self._events.put_nowait(retry_event(attempt, max_attempts, reason))

    def error(self, node_name: str, error_msg: str):
        """Called when an error occurs."""
        self._events.put_nowait(error_event(node_name, error_msg))

    def complete(self, final_state: TaskState, total_duration_ms: float):
        """Called when workflow finishes."""
        self.state = final_state
        self._events.put_nowait(result_event(
            task_id=self.task_id,
            status=final_state.status.value,
            generated_code=final_state.generated_code,
            error=final_state.error_message,
            total_duration_ms=total_duration_ms,
        ))
        self._events.put_nowait(None)  # Signal done

    # === SSE reads from this ===

    async def progress(self):
        """Yield events as they happen."""
        while True:
            event = await self._events.get()
            if event is None:
                break
            yield event
