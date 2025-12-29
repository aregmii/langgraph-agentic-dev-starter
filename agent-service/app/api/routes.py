"""
API Routes

REST endpoints for the code agent:
- POST /tasks - Submit a new coding task
- GET /tasks/{task_id} - Get task status and result
"""

from uuid import uuid4
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.core.task_state import TaskState, TaskType, TaskStatus


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

@router.post("", response_model=TaskResponse)
async def create_task(request: TaskRequest) -> TaskResponse:
    """
    Create and execute a coding task.
    
    For now, runs synchronously. Module 5 adds async Redis queue.
    """
    from app.agents.code_agent import create_code_agent
    from app.llm.grok_client import GrokClient
    
    # Create initial state
    task_id = str(uuid4())
    state = TaskState(
        task_id=task_id,
        task_type=TaskType.CODE_GENERATION,  # Overwritten by identifier
        input_description=request.description,
        context=request.context,
    )
    
    # Create and run agent
    llm_client = GrokClient()
    agent = create_code_agent(
        identifier_llm=llm_client,
        executor_llm=llm_client,
    )
    
    # Run the workflow
    result = await agent.ainvoke(state)

    if isinstance(result, dict):
        final_state = TaskState(**result)
    else:
        final_state = result
    
    # Store result
    tasks[task_id] = final_state
    
    return TaskResponse.from_state(final_state)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str) -> TaskResponse:
    """Get the status and result of a task."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskResponse.from_state(tasks[task_id])