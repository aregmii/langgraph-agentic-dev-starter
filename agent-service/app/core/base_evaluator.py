"""
Base Evaluator Interface

Evaluators assess the quality of agent output.
Used to decide if output is good enough or needs retry.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from app.core.task_state import TaskState


@dataclass
class EvaluationResult:
    """Result of evaluating agent output."""
    score: float  # 0.0 to 1.0
    passed: bool  # Did it meet the threshold?
    feedback: str  # Explanation of the evaluation


class BaseEvaluator(ABC):
    """
    Abstract base class for evaluation strategies.
    
    Evaluators check if the generated output is acceptable.
    If not, the agent can retry with the feedback.
    
    Strategies could be:
    - Rule-based: Check syntax, run tests
    - LLM-as-judge: Ask another LLM to evaluate
    - Hybrid: Rules first, LLM for edge cases
    """
    
    @abstractmethod
    async def evaluate(self, state: TaskState) -> EvaluationResult:
        """
        Evaluate the output in the given state.
        
        Args:
            state: TaskState containing generated_code and other context
            
        Returns:
            EvaluationResult with score, pass/fail, and feedback
        """
        pass
    
    @property
    @abstractmethod
    def threshold(self) -> float:
        """Minimum score (0.0-1.0) required to pass evaluation."""
        pass