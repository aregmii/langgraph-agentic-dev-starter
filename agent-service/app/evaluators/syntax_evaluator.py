"""
Syntax Evaluator

Simple evaluator that checks if generated code is valid Python.
Fast first-pass check before more expensive evaluations.
"""

import ast
from app.core.base_evaluator import BaseEvaluator, EvaluationResult
from app.core.task_state import TaskState


class SyntaxEvaluator(BaseEvaluator):
    """
    Evaluates code by checking if it parses as valid Python.

    //TODO For production, combine with:
    - CodeExecutionEvaluator: Actually run the code
    - LLMEvaluator: Ask an LLM to judge quality
    - TestEvaluator: Run against test cases
    """
    
    @property
    def threshold(self) -> float:
        return 1.0  # Syntax check is pass/fail
    
    async def evaluate(self, state: TaskState) -> EvaluationResult:
        """
        Check if generated code is syntactically valid Python.
        """
        code = state.generated_code
        
        if not code or not code.strip():
            return EvaluationResult(
                score=0.0,
                passed=False,
                feedback="No code was generated"
            )
        
        try:
            ast.parse(code)
            return EvaluationResult(
                score=1.0,
                passed=True,
                feedback="Code is syntactically valid"
            )
        except SyntaxError as e:
            return EvaluationResult(
                score=0.0,
                passed=False,
                feedback=f"Syntax error at line {e.lineno}: {e.msg}"
            )