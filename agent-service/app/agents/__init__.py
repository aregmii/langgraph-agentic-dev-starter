"""Agent implementations."""

# Legacy agents (kept for backwards compatibility)
from app.agents.code_agent import CodeAgent
from app.agents.task_execution import TaskExecution

# Module 12: Multi-agent system
from app.agents.manager import ManagerAgent
from app.agents.builder import SoftwareBuilderAgent
from app.agents.reviewer import SoftwareReviewerAgent
from app.agents.docgen import DocumentationGeneratorAgent

__all__ = [
    # Legacy
    "CodeAgent",
    "TaskExecution",
    # Module 12
    "ManagerAgent",
    "SoftwareBuilderAgent",
    "SoftwareReviewerAgent",
    "DocumentationGeneratorAgent",
]
