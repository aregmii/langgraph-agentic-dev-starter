"""
Code Agent Workflow

LangGraph workflow that:
1. Identifies the task type
2. Generates code using appropriate prompt
3. Evaluates output, retries if needed
"""

from langgraph.graph import StateGraph, END

from app.core.task_state import TaskState, TaskStatus
from app.core.base_llm import BaseLLMClient
from app.classifier.task_identifier import TaskIdentifier
from app.executors.code_executor import CodeExecutor
from app.evaluators.syntax_evaluator import SyntaxEvaluator


def create_code_agent(
    identifier_llm: BaseLLMClient,
    executor_llm: BaseLLMClient,
) -> StateGraph:
    """
    Create the code agent workflow.
    
    Args:
        identifier_llm: LLM for task identification (can be smaller/cheaper)
        executor_llm: LLM for code generation (should be powerful)
        
    Returns:
        Compiled workflow ready to execute
    """
    
    # Initialize components
    identifier = TaskIdentifier(identifier_llm)
    executor = CodeExecutor(executor_llm)
    evaluator = SyntaxEvaluator()
    
    # ===== NODE FUNCTIONS =====
    
    async def identify_node(state: TaskState) -> TaskState:
        """Identify the task type."""
        # Mark that we're starting identification
        state = state.with_updates(status=TaskStatus.IDENTIFYING)
        
        # Check if we can handle this at all
        if not await identifier.can_handle(state):
            return state.with_updates(
                status=TaskStatus.FAILED,
                error_message="Not a coding task - cannot handle"
            )
        
        # Identify the task type
        task_type = await identifier.identify(state)
        
        return state.with_updates(task_type=task_type)
    
    async def execute_node(state: TaskState) -> TaskState:
        """Generate code using the LLM."""
        # Mark that we're starting execution
        state = state.with_updates(status=TaskStatus.EXECUTING)
        
        # Execute and return updated state
        return await executor.execute(state)
    
    async def evaluate_node(state: TaskState) -> TaskState:
        """Check if generated code is acceptable."""
        # Mark that we're starting evaluation
        state = state.with_updates(status=TaskStatus.EVALUATING)
        
        result = await evaluator.evaluate(state)
        
        if result.passed:
            return state.with_updates(
                status=TaskStatus.COMPLETED,
                evaluation_score=result.score,
                evaluation_feedback=result.feedback
            )
        
        # Failed - can we retry?
        if state.is_retriable():
            return state.increment_retry().with_updates(
                evaluation_score=result.score,
                evaluation_feedback=result.feedback
            )
        
        # No retries left
        return state.with_updates(
            status=TaskStatus.FAILED,
            evaluation_score=result.score,
            evaluation_feedback=result.feedback,
            error_message="Max retries exceeded"
        )
    
    # ===== EDGE FUNCTIONS =====
    # These return a STRING that maps to the next node
    
    def after_identify(state: TaskState) -> str:
        """After identification, go to execute or end."""
        if state.status == TaskStatus.FAILED:
            return "end"
        return "execute"
    
    def after_evaluate(state: TaskState) -> str:
        """After evaluation, retry, complete, or fail."""
        if state.status == TaskStatus.COMPLETED:
            return "end"
        if state.status == TaskStatus.FAILED:
            return "end"
        if state.status == TaskStatus.RETRYING:
            return "execute"
        return "end"
    
    # ===== BUILD THE WORKFLOW =====
    
    workflow = StateGraph(TaskState)
    
    # Register the nodes
    workflow.add_node("identify", identify_node)
    workflow.add_node("execute", execute_node)
    workflow.add_node("evaluate", evaluate_node)
    
    # Start at identify
    workflow.set_entry_point("identify")
    
    # After identify: check after_identify() to decide next step
    # If returns "execute" → go to execute node
    # If returns "end" → stop workflow
    workflow.add_conditional_edges(
        "identify",
        after_identify,
        {"execute": "execute", "end": END}
    )
    
    # After execute: always go to evaluate
    workflow.add_edge("execute", "evaluate")
    
    # After evaluate: check after_evaluate() to decide next step
    # If returns "execute" → retry (go back to execute)
    # If returns "end" → stop workflow
    workflow.add_conditional_edges(
        "evaluate",
        after_evaluate,
        {"execute": "execute", "end": END}
    )
    
    return workflow.compile()