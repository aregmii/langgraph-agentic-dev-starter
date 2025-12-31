"""
Code Agent

Executes coding tasks with observable progress via TaskExecution.
"""

import asyncio
import time
from uuid import uuid4

from app.core.task_state import TaskState, TaskType, TaskStatus
from app.core.base_llm import BaseLLMClient
from app.classifier.task_identifier import TaskIdentifier
from app.executors.code_executor import CodeExecutor
from app.evaluators.syntax_evaluator import SyntaxEvaluator
from app.agents.task_execution import TaskExecution
from app.logging_utils import (
    log_node_start,
    log_node_complete,
    log_workflow_complete,
    log_retry,
    log_error,
)


class CodeAgent:
    """
    Agent that executes coding tasks.

    Usage:
        agent = CodeAgent(llm_client)
        execution = agent.initiate_task("Write a sort function", None)

        async for event in execution.progress():
            print(event.to_sse())
    """

    def __init__(self, identifier_llm: BaseLLMClient, executor_llm: BaseLLMClient):
        self.identifier = TaskIdentifier(identifier_llm)
        self.executor = CodeExecutor(executor_llm)
        self.evaluator = SyntaxEvaluator()

    def initiate_task(self, description: str, context: str | None = None) -> TaskExecution:
        """
        Start a task and return the execution handle.

        The task runs in the background. Use execution.progress() to get events.
        """
        task_id = str(uuid4())
        state = TaskState(
            task_id=task_id,
            task_type=TaskType.CODE_GENERATION,  # Will be overwritten
            input_description=description,
            context=context,
        )

        execution = TaskExecution(task_id, state)

        # Run workflow in background
        asyncio.create_task(self._run(execution, state))

        return execution

    async def _run(self, execution: TaskExecution, state: TaskState):
        """Execute the workflow, updating the execution object."""
        workflow_start = time.time()

        try:
            # === IDENTIFY ===
            execution.start_node("identify", f"Analyzing: '{state.input_description[:50]}...'")
            log_node_start(state.task_id, "identify", f"Analyzing: '{state.input_description[:50]}...'")

            state = state.with_updates(status=TaskStatus.IDENTIFYING)

            if not await self.identifier.can_handle(state):
                execution.complete_node("identify", "Not a coding task")
                log_node_complete(state.task_id, "identify", "Not a coding task", "failed")
                state = state.with_updates(
                    status=TaskStatus.FAILED,
                    error_message="Not a coding task - cannot handle"
                )
                execution.complete(state, (time.time() - workflow_start) * 1000)
                return

            task_type = await self.identifier.identify(state)
            state = state.with_updates(task_type=task_type)

            execution.complete_node("identify", f"Task type: {task_type.value}")
            log_node_complete(state.task_id, "identify", f"Task type: {task_type.value}")

            # === EXECUTE (with retry loop) ===
            max_retries = state.max_retries

            while True:
                execution.start_node("execute", f"Generating code for {state.task_type.value}...")
                log_node_start(state.task_id, "execute", f"Generating code for {state.task_type.value}...")

                state = state.with_updates(status=TaskStatus.EXECUTING)
                state = await self.executor.execute(state)

                execution.complete_node("execute", f"Generated {len(state.generated_code or '')} chars")
                log_node_complete(state.task_id, "execute", f"Generated {len(state.generated_code or '')} chars")

                # === EVALUATE ===
                execution.start_node("evaluate", "Validating syntax...")
                log_node_start(state.task_id, "evaluate", "Validating syntax...")

                state = state.with_updates(status=TaskStatus.EVALUATING)
                result = await self.evaluator.evaluate(state)

                if result.passed:
                    state = state.with_updates(
                        status=TaskStatus.COMPLETED,
                        evaluation_score=result.score,
                        evaluation_feedback=result.feedback
                    )
                    execution.complete_node("evaluate", f"Passed! Score: {result.score}")
                    log_node_complete(state.task_id, "evaluate", f"Passed! Score: {result.score}")
                    break

                # Failed - can we retry?
                if state.is_retriable():
                    state = state.increment_retry()
                    execution.complete_node("evaluate", f"Failed: {result.feedback}")
                    execution.retry(state.retry_count, max_retries, result.feedback)
                    log_retry(state.task_id, state.retry_count, max_retries, result.feedback)
                    # Loop continues to execute again
                else:
                    state = state.with_updates(
                        status=TaskStatus.FAILED,
                        evaluation_score=result.score,
                        evaluation_feedback=result.feedback,
                        error_message="Max retries exceeded"
                    )
                    execution.complete_node("evaluate", "Max retries exceeded")
                    execution.error("evaluate", "Max retries exceeded")
                    log_error(state.task_id, "evaluate", "Max retries exceeded")
                    break

            # === COMPLETE ===
            total_duration = (time.time() - workflow_start) * 1000
            execution.complete(state, total_duration)
            log_workflow_complete(state.task_id)

        except Exception as e:
            execution.error("workflow", str(e))
            log_error(state.task_id, "workflow", str(e))
            state = state.with_updates(
                status=TaskStatus.FAILED,
                error_message=str(e)
            )
            execution.complete(state, (time.time() - workflow_start) * 1000)
