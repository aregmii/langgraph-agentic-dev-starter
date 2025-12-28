"""
Base Router Interface

This module defines the interface for task routing strategies.
The router examines incoming tasks and decides which executor
should handle them.

Routing strategies could be rule-based, LLM-based, semantic similarity etc
"""

from abc import ABC, abstractmethod
from app.core.task_state import TaskState, TaskType


class BaseRouter(ABC):
    """
    Abstract base class for routing strategies.
    
    The router's job is to examine a task and decide:
    1. What type of task is this? (TaskType)
    2. Should we accept or reject it?
    
    Extension point: Create new implementations in agent-service/app/routers/
    """
    
    @abstractmethod
    async def route(self, state: TaskState) -> TaskType:
        """
        Determine the task type for a given state.
        
        Args:
            state: Current task state with input_description
            
        Returns:
            TaskType indicating which executor should handle this
        """
        pass
    
    @abstractmethod
    async def can_handle(self, state: TaskState) -> bool:
        """
        Check if this agent can handle the given task.
        
        Use this to reject tasks that are out of scope
        (e.g., "write me a poem" to a coding agent).
        
        Args:
            state: Current task state
            
        Returns:
            True if agent can handle, False to reject
        """
        pass