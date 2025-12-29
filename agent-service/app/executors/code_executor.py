"""
Code Executor

Calls the LLM to generate/modify code based on task type.
"""

from app.core.base_llm import BaseLLMClient
from app.core.task_state import TaskState, TaskType, TaskStatus
from app.executors.prompts import (
    CODE_GENERATION_SYSTEM, CODE_GENERATION_TEMPLATE,
    CODE_FIX_SYSTEM, CODE_FIX_TEMPLATE,
    CODE_REFACTOR_SYSTEM, CODE_REFACTOR_TEMPLATE,
    CODE_TESTING_SYSTEM, CODE_TESTING_TEMPLATE,
    CODE_REVIEW_SYSTEM, CODE_REVIEW_TEMPLATE,
    format_context_section,
)


class CodeExecutor:
    """
    Executes coding tasks by calling the LLM with appropriate prompts.
    
    Selects the right prompt based on TaskType, calls the LLM,
    and returns updated state with generated code.
    """
    
    # Map task types to their prompts
    PROMPTS: dict[TaskType, tuple[str, str]] = {
        TaskType.CODE_GENERATION: (CODE_GENERATION_SYSTEM, CODE_GENERATION_TEMPLATE),
        TaskType.CODE_FIX: (CODE_FIX_SYSTEM, CODE_FIX_TEMPLATE),
        TaskType.CODE_REFACTOR: (CODE_REFACTOR_SYSTEM, CODE_REFACTOR_TEMPLATE),
        TaskType.CODE_TESTING: (CODE_TESTING_SYSTEM, CODE_TESTING_TEMPLATE),
        TaskType.CODE_REVIEW: (CODE_REVIEW_SYSTEM, CODE_REVIEW_TEMPLATE),
    }
    
    def __init__(self, llm_client: BaseLLMClient):
        self.llm_client = llm_client
    
    async def execute(self, state: TaskState) -> TaskState:
        """
        Execute the task by calling the LLM.
        
        Args:
            state: Current task state with task_type determined
            
        Returns:
            Updated state with generated_code populated
        """
        system_prompt, template = self.PROMPTS[state.task_type]
        
        # Build the prompt
        if state.task_type == TaskType.CODE_GENERATION:
                prompt = template.format(
                    user_input=state.input_description,
                    context_section=format_context_section(state.context),
                )

        else:
            prompt = template.format(
                user_input=state.input_description,
                existing_code=state.context or "No code provided",
            )

        # Call LLM
        if state.context:
            response = await self.llm_client.generate_with_context(
                prompt=state.input_description,
                context=state.context,
                system_prompt=system_prompt,
            )
        else:
            response = await self.llm_client.generate(
                prompt=prompt,
                system_prompt=system_prompt,
            )
        
        # Return updated state
        return state.with_updates(
            status=TaskStatus.EVALUATING,
            generated_code=strip_markdown_code_blocks(response.content),
        )

def strip_markdown_code_blocks(text: str) -> str:
    """Remove markdown code blocks from LLM response."""
    import re
    # Match ```python ... ``` or ``` ... ```
    pattern = r'```(?:python)?\n?(.*?)```'
    matches = re.findall(pattern, text, re.DOTALL)
    if matches:
        return matches[0].strip()
    return text.strip()