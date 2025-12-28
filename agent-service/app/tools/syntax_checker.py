"""
Syntax Checker Tool

Validates that generated code is syntactically correct Python.
Fast check that doesn't execute any code.
"""

import ast
from app.core.base_tool import BaseTool, ToolResult


class SyntaxChecker(BaseTool):
    """
    Checks if Python code is syntactically valid.
    
    Uses Python's ast module to parse code without executing it.
    This is safe and fast - good as a first validation step.
    """
    
    @property
    def name(self) -> str:
        return "syntax_checker"
    
    @property
    def description(self) -> str:
        return "Checks if Python code is syntactically valid without executing it"
    
    async def execute(self, code: str) -> ToolResult:
        """
        Parse the code and check for syntax errors.
        
        Args:
            code: Python code to validate
            
        Returns:
            ToolResult with success=True if valid, False with error details if not
        """
        if not code or not code.strip():
            return ToolResult(
                success=False,
                output=None,
                error_message="Empty code provided"
            )
        
        try:
            ast.parse(code)
            return ToolResult(
                success=True,
                output="Syntax is valid",
                error_message=None
            )
        except SyntaxError as e:
            return ToolResult(
                success=False,
                output=None,
                error_message=f"Line {e.lineno}: {e.msg}"
            )