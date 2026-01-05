"""
Code Executor Tool

Executes Python code in a subprocess and captures output.
"""

import subprocess
import re
from app.core.base_tool import BaseTool, ToolResult


# Known GUI/game modules that can't run in headless mode
GUI_MODULES = {
    "pygame": "pip install pygame",
    "tkinter": "(built-in, requires display)",
    "turtle": "(built-in, requires display)",
    "pyglet": "pip install pyglet",
    "arcade": "pip install arcade",
    "kivy": "pip install kivy",
    "PyQt5": "pip install PyQt5",
    "PyQt6": "pip install PyQt6",
    "PySide6": "pip install PySide6",
    "wx": "pip install wxPython",
}


def _format_module_error(stderr: str) -> str | None:
    """Check if error is a missing module and return helpful message."""
    # Match "ModuleNotFoundError: No module named 'xyz'"
    match = re.search(r"ModuleNotFoundError: No module named ['\"](\w+)['\"]", stderr)
    if not match:
        return None

    module = match.group(1)

    if module in GUI_MODULES:
        install_hint = GUI_MODULES[module]
        return (
            f"⚠️ This code requires '{module}' which is a GUI/game library.\n\n"
            f"To run this code locally:\n"
            f"1. Install the module: {install_hint}\n"
            f"2. Run in an environment with a display (not headless server)\n\n"
            f"The code itself is correct - it just needs the right environment to run!"
        )
    else:
        return (
            f"⚠️ Missing module: '{module}'\n\n"
            f"To run this code, install the module:\n"
            f"  pip install {module}\n\n"
            f"The code itself is correct - it just needs this dependency installed."
        )


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
                # Check for missing module errors and provide helpful message
                friendly_error = _format_module_error(result.stderr)
                if friendly_error:
                    return ToolResult(
                        success=False,
                        output=None,
                        error_message=friendly_error
                    )

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