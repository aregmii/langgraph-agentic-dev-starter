"""
API Routes

REST endpoints for the code agent:
- POST /tasks - Submit a new coding task (uses ManagerAgent)
- GET /tasks/{task_id} - Get task status and result
- POST /tasks/execute - Execute code directly
"""

import asyncio
import json
import os
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.core.task_state import TaskState, TaskStatus, TaskType
from app.logging_utils import log_request_start, log_request_complete, log_request_failed
from app.tools.code_executor import CodeExecutor
from app.api.workflow_events import result_event

from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/tasks", tags=["tasks"])


# ===== REQUEST/RESPONSE MODELS =====

class TaskRequest(BaseModel):
    """Request body for creating a new task."""
    description: str
    context: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "description": "Write a Python function to sort a list",
                "context": None
            }
        }


class TaskResponse(BaseModel):
    """Response body for task operations."""
    task_id: str
    status: str
    task_type: Optional[str] = None
    generated_code: Optional[str] = None
    evaluation_score: Optional[float] = None
    evaluation_feedback: Optional[str] = None
    error_message: Optional[str] = None

    @classmethod
    def from_state(cls, state: TaskState) -> "TaskResponse":
        """Convert TaskState to API response."""
        return cls(
            task_id=state.task_id,
            status=state.status.value,
            task_type=state.task_type.value if state.task_type else None,
            generated_code=state.generated_code,
            evaluation_score=state.evaluation_score,
            evaluation_feedback=state.evaluation_feedback,
            error_message=state.error_message,
        )


# ===== IN-MEMORY STORAGE (replace with Redis in Module 5) =====

tasks: dict[str, TaskState] = {}


# ===== ENDPOINTS =====

@router.post("", response_class=StreamingResponse)
async def create_task(request: TaskRequest):
    """
    Create and execute a coding task using the multi-agent system.

    Returns Server-Sent Events (SSE) showing real-time progress.

    Flow (Module 12 - ManagerAgent):
    1. Manager creates execution plan
    2. For each stage:
       - Builder generates code
       - Reviewer validates (with reflection loop on failure)
    3. DocGen adds documentation
    4. Manager assembles final result

    SSE Events:
    - manager_planning_start, manager_planning_complete
    - stage_start, stage_complete
    - manager_delegating, builder_complete, reviewer_complete
    - reflection_start, reflection_complete (on retry)
    - docgen_complete
    - manager_complete
    - result (final output)
    """
    from app.llm import get_registry
    from app.agents.manager import ManagerAgent

    task_id = f"task-{uuid.uuid4().hex[:8]}"

    # Log request start
    mock_mode = os.getenv("USE_MOCK_LLM", "false").lower() == "true"
    log_request_start(task_id, request.description, request.context, mock_mode)

    # Get LLM client from registry
    llm_client = get_registry().get("coder")

    # Async queue for real-time event streaming
    event_queue: asyncio.Queue[dict | None] = asyncio.Queue()

    def event_callback(event_name: str, data: dict) -> None:
        """Callback to push events to queue for real-time streaming."""
        import datetime
        event_data = {
            "event": event_name,
            "timestamp": datetime.datetime.now().isoformat(),
            **data
        }
        # Put event in queue (non-blocking for sync callback)
        try:
            event_queue.put_nowait(event_data)
        except asyncio.QueueFull:
            pass  # Drop event if queue is full (shouldn't happen)

    # Create manager with event callback
    manager = ManagerAgent(
        llm_client=llm_client,
        event_callback=event_callback,
    )

    async def run_manager():
        """Run the manager and signal completion."""
        try:
            result = await manager.run(request.description)
            await event_queue.put({"_result": result})
        except Exception as e:
            await event_queue.put({"_error": str(e)})
        finally:
            await event_queue.put(None)  # Signal end

    async def event_generator():
        # Start manager in background task
        manager_task = asyncio.create_task(run_manager())

        result = None
        error = None

        try:
            while True:
                event_data = await event_queue.get()

                if event_data is None:
                    # End signal
                    break

                if "_result" in event_data:
                    result = event_data["_result"]
                    continue

                if "_error" in event_data:
                    error = event_data["_error"]
                    continue

                # Stream the event immediately
                json_data = json.dumps(event_data)
                yield f"data: {json_data}\n\n"

            # Emit final result
            if result:
                final_event = result_event(
                    task_id=task_id,
                    status="completed" if result.success else "failed",
                    generated_code=result.code,
                    error=result.error_message,
                    total_duration_ms=result.duration_ms,
                )
                yield final_event.to_sse()

                log_request_complete(
                    task_id,
                    result.duration_ms,
                    "completed" if result.success else "failed",
                    len(result.code)
                )

                tasks[task_id] = TaskState(
                    task_id=task_id,
                    task_type=TaskType.CODE_GENERATION,
                    input_description=request.description,
                    context=request.context,
                    status=TaskStatus.COMPLETED if result.success else TaskStatus.FAILED,
                    generated_code=result.code,
                    evaluation_score=1.0 if result.success else 0.0,
                    evaluation_feedback=f"Generated {result.code_lines} lines of code",
                )
            elif error:
                error_event_data = {
                    "event": "error",
                    "error": error,
                    "task_id": task_id,
                }
                yield f"data: {json.dumps(error_event_data)}\n\n"

                log_request_failed(task_id, 0, error)

                tasks[task_id] = TaskState(
                    task_id=task_id,
                    task_type=TaskType.CODE_GENERATION,
                    input_description=request.description,
                    context=request.context,
                    status=TaskStatus.FAILED,
                    error_message=error,
                )

        except Exception as e:
            error_event_data = {
                "event": "error",
                "error": str(e),
                "task_id": task_id,
            }
            yield f"data: {json.dumps(error_event_data)}\n\n"
            log_request_failed(task_id, 0, str(e))

        finally:
            # Ensure manager task is done
            await manager_task

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str) -> TaskResponse:
    """Get the status and result of a task."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskResponse.from_state(tasks[task_id])


# ===== CODE EXECUTION =====

# Initialize code executor
code_executor = CodeExecutor()


class ExecuteRequest(BaseModel):
    """Request to execute Python code."""
    code: str


class ExecuteResponse(BaseModel):
    """Response from code execution."""
    success: bool
    output: str
    error: str | None = None
    execution_time_ms: float


@router.post("/execute", response_model=ExecuteResponse)
async def execute_code(request: ExecuteRequest):
    """Execute Python code and return output."""
    import time
    start = time.time()

    result = await code_executor.execute(request.code)

    execution_time = (time.time() - start) * 1000

    return ExecuteResponse(
        success=result.success,
        output=result.output or "(No output)",
        error=result.error_message if not result.success else None,
        execution_time_ms=round(execution_time, 1)
    )
