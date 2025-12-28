"""
Base Tool Interface

Tools are capabilities the agent can use during execution.
Examples: run code, search documentation, read files, call APIs.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolResult:
    """Standardized result from any tool execution."""
    success: bool
    output: Any
    error_message: str | None = None


class BaseTool(ABC):
    """
    Abstract base class for agent tools.
    
    Tools extend what the agent can do beyond just calling an LLM.
    Each tool has a name, description (for LLM to understand when to use it),
    and an execute method.
    
    Extension point: Create new tools in agent-service/app/tools/
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this tool."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """
        Description of what this tool does.
        
        This is shown to the LLM so it knows when to use this tool.
        Be clear and specific.
        """
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with given parameters.
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            ToolResult with success status and output
        """
        pass