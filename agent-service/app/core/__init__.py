"""
Core interfaces and data structures.

All base classes are defined here. Implementations live in
their respective directories (llm/, routers/, tools/, evaluators/).
"""

from app.core.task_state import TaskState, TaskType, TaskStatus
from app.core.base_llm import BaseLLMClient, LLMResponse
from app.core.base_router import BaseRouter
from app.core.base_tool import BaseTool, ToolResult
from app.core.base_evaluator import BaseEvaluator, EvaluationResult

__all__ = [
    # State
    "TaskState",
    "TaskType", 
    "TaskStatus",
    # LLM
    "BaseLLMClient",
    "LLMResponse",
    # Router
    "BaseRouter",
    # Tools
    "BaseTool",
    "ToolResult",
    # Evaluator
    "BaseEvaluator",
    "EvaluationResult",
]