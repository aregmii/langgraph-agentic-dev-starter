"""
API Routes

REST endpoints for the code agent:
- POST /tasks - Submit a new coding task
- GET /tasks/{task_id} - Get task status and result
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.core.task_state import TaskState

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

    # Store for GET endpoint
    tasks[execution.task_id] = execution.state

    async def event_generator():
        async for event in execution.progress():
            yield event.to_sse()
        # Update stored state after completion
        tasks[execution.task_id] = execution.state

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
