"""
Code Executor Tool

Executes Python code in a subprocess and captures output.
"""

import subprocess
from app.core.base_tool import BaseTool, ToolResult


class CodeExecutor(BaseTool):
    """
    Executes Python code in a separate process.
    
    Uses subprocess for isolation - the executed code runs in a
    completely separate Python process and cannot affect our application.
    
    For production, consider Docker-based execution for full sandboxing.
    """
    
    def __init__(self, timeout_seconds: int = 5):
        self.timeout_seconds = timeout_seconds
    
    @property
    def name(self) -> str:
        return "code_executor"
    
    @property
    def description(self) -> str:
        return "Executes Python code and returns the output or error"
    
    async def execute(self, code: str) -> ToolResult:
        """
        Execute Python code in a subprocess with timeout.
        
        Args:
            code: Python code to execute
            
        Returns:
            ToolResult with captured output or error message
        """
        if not code or not code.strip():
            return ToolResult(
                success=False,
                output=None,
                error_message="Empty code provided"
            )
        
        try:
            result = subprocess.run(
                ["python", "-c", code],
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds
            )
            
            if result.returncode == 0:
                return ToolResult(
                    success=True,
                    output=result.stdout if result.stdout else "Code executed successfully (no output)",
                    error_message=None
                )
            else:
                return ToolResult(
                    success=False,
                    output=result.stdout,
                    error_message=result.stderr
                )
                
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                output=None,
                error_message=f"Execution timed out after {self.timeout_seconds} seconds"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error_message=f"{type(e).__name__}: {str(e)}"
            )