"""Documentation Generator Agent - Adds docstrings and generates README.

The DocGen Agent:
1. Receives validated code from all completed steps
2. Adds/improves docstrings to functions and classes
3. Generates a README with project description and usage
4. Returns DocumentedCode to Manager

Uses 1 LLM call.
"""

from typing import Callable

from app.core.base_llm import BaseLLMClient
from app.models.agents import AgentType
from app.models.execution import CompletedStep, DocumentedCode


DOCGEN_SYSTEM_PROMPT = """You are an expert technical writer specializing in Python documentation.

Your task is to:
1. Add comprehensive docstrings to all functions and classes
2. Generate a clear README.md with usage examples

Follow Google-style docstrings. Include:
- Brief description
- Args with types and descriptions
- Returns with type and description
- Raises if applicable

For the README:
- Project title and description
- How to run the code
- Example usage
- Requirements (if any external libraries)
"""

DOCGEN_TEMPLATE = """PROJECT: {project_goal}

CODE TO DOCUMENT:
```python
{code}
```

Please:
1. Add/improve docstrings for all functions and classes
2. Generate a README.md

Return your response in this EXACT format:

=== DOCUMENTED CODE ===
<the code with improved docstrings - NO markdown blocks>

=== README ===
<markdown README content>
"""


def _parse_docgen_response(response: str, original_code: str) -> tuple[str, str]:
    """Parse docgen response into documented code and readme."""
    import re

    code = ""
    readme = ""

    if "=== DOCUMENTED CODE ===" in response and "=== README ===" in response:
        parts = response.split("=== README ===")
        if len(parts) == 2:
            code_part = parts[0].replace("=== DOCUMENTED CODE ===", "").strip()
            readme_part = parts[1].strip()

            # Strip markdown blocks if present
            if "```python" in code_part:
                match = re.search(r'```python\n?(.*?)```', code_part, re.DOTALL)
                code = match.group(1).strip() if match else code_part
            elif "```" in code_part:
                match = re.search(r'```\n?(.*?)```', code_part, re.DOTALL)
                code = match.group(1).strip() if match else code_part
            else:
                code = code_part

            if "```markdown" in readme_part:
                match = re.search(r'```markdown\n?(.*?)```', readme_part, re.DOTALL)
                readme = match.group(1).strip() if match else readme_part
            else:
                readme = readme_part
    else:
        # Fallback - return original code and basic readme
        code = original_code
        readme = "# Project\n\nGenerated code project."

    return code, readme


class DocumentationGeneratorAgent:
    """Generates documentation for completed code.

    Uses 1 LLM call to add docstrings and generate README.
    """

    agent_type: AgentType = AgentType.DOCGEN

    def __init__(
        self,
        llm_client: BaseLLMClient,
        agent_id: str = "docgen-1",
        event_callback: Callable[[str, dict], None] | None = None,
    ):
        self.llm_client = llm_client
        self.agent_id = agent_id
        self.event_callback = event_callback or (lambda e, d: None)

    def _emit(self, event: str, data: dict) -> None:
        """Emit an event with agent context."""
        self.event_callback(event, {"agent_id": self.agent_id, **data})

    async def execute(self, completed_steps: list[CompletedStep], project_goal: str) -> DocumentedCode:
        """Generate documentation for all completed code.

        Args:
            completed_steps: List of validated steps with code
            project_goal: Overall project description

        Returns:
            DocumentedCode with documented code and README
        """
        self._emit("docgen_start", {"code_lines": sum(s.code_lines for s in completed_steps)})

        # Combine all code from completed steps
        combined_code_parts = []
        for step in completed_steps:
            combined_code_parts.append(step.code)

        combined_code = "\n\n".join(combined_code_parts)

        prompt = DOCGEN_TEMPLATE.format(
            project_goal=project_goal,
            code=combined_code,
        )

        response = await self.llm_client.generate(
            prompt=prompt,
            system_prompt=DOCGEN_SYSTEM_PROMPT,
        )

        documented_code, readme = _parse_docgen_response(response.content, combined_code)

        return DocumentedCode(
            code=documented_code,
            readme=readme,
        )


__all__ = ["DocumentationGeneratorAgent"]
