"""Manager Agent package.

Two implementations available:
- LangGraphManager: Uses LangGraph StateGraph (recommended for interviews)
- ManagerAgent: Original custom implementation (legacy)

The default export uses LangGraph for demonstration purposes.
"""

from .langgraph_manager import LangGraphManager, AgentState

# Use LangGraph implementation as the default
ManagerAgent = LangGraphManager

__all__ = ["ManagerAgent", "LangGraphManager", "AgentState"]
