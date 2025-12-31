"""
API Routes

REST endpoints for the code agent:
- POST /tasks - Submit a new coding task
- GET /tasks/{task_id} - Get task status and result
"""

import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.core.task_state import TaskState
from app.logging_utils import log_request_start, log_request_complete, log_request_failed
from app.tools.code_executor import CodeExecutor

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
    Create and execute a coding task.

    Returns Server-Sent Events (SSE) showing real-time progress.
    """
    from app.agents.code_agent import CodeAgent
    from app.llm import get_llm_client

    llm_client = get_llm_client()
    agent = CodeAgent(
        identifier_llm=llm_client,
        executor_llm=llm_client,
    )

    execution = agent.initiate_task(request.description, request.context)

    # Log request start
    mock_mode = os.getenv("USE_MOCK_LLM", "false").lower() == "true"
    log_request_start(execution.task_id, request.description, request.context, mock_mode)

    # Store for GET endpoint
    tasks[execution.task_id] = execution.state

    async def event_generator():
        last_event = None
        async for event in execution.progress():
            last_event = event
            yield event.to_sse()

        # Log completion
        final_state = execution.state
        total_ms = 0
        if last_event and hasattr(last_event, 'data') and 'total_duration_ms' in last_event.data:
            total_ms = last_event.data['total_duration_ms']

        if final_state.status.value == "completed":
            log_request_complete(
                execution.task_id,
                total_ms,
                final_state.status.value,
                len(final_state.generated_code or "")
            )
        else:
            log_request_failed(
                execution.task_id,
                total_ms,
                final_state.error_message or "Unknown error"
            )

        tasks[execution.task_id] = final_state

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
