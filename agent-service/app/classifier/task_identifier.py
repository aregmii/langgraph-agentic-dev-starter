"""
Task Identifier

Uses an LLM to identify what type of coding task the user is requesting.
"""

from app.core.base_llm import BaseLLMClient
from app.core.task_state import TaskState, TaskType
from app.classifier.prompts import (
    IDENTIFIER_SYSTEM_PROMPT,
    IDENTIFIER_TEMPLATE,
    CAN_HANDLE_TEMPLATE,
)


class TaskIdentifier:
    """
    Identifies the type of coding task from user input.
    
    The identified TaskType determines which prompt template
    the executor uses when calling the LLM.
    """
    
    def __init__(self, llm_client: BaseLLMClient):
        self.llm_client = llm_client
    
    async def identify(self, state: TaskState) -> TaskType:
        """Identify the task type from the input description."""
        prompt = IDENTIFIER_TEMPLATE.format(
            user_input=state.input_description
        )
        
        response = await self.llm_client.generate(
            prompt=prompt,
            system_prompt=IDENTIFIER_SYSTEM_PROMPT,
            temperature=0.0,
            max_tokens=50,
        )
        
        return self._parse_response(response.content)
    
    async def can_handle(self, state: TaskState) -> bool:
        """Check if this is a coding task we can handle."""
        prompt = CAN_HANDLE_TEMPLATE.format(
            user_input=state.input_description
        )
        
        response = await self.llm_client.generate(
            prompt=prompt,
            temperature=0.0,
            max_tokens=10,
        )
        
        return response.content.strip().upper().startswith("YES")
    
    def _parse_response(self, response: str) -> TaskType:
        """Parse LLM response into TaskType enum."""
        cleaned = response.strip().upper().replace(" ", "_")
        
        for task_type in TaskType:
            if task_type.name in cleaned or cleaned in task_type.name:
                return task_type
        
        return TaskType.CODE_GENERATION