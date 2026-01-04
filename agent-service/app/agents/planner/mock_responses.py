"""
Mock LLM responses for testing the Planner Agent.

Provides deterministic responses for common task types to enable
testing without hitting a real LLM API.
"""

import json

# Mock responses keyed by task pattern
MOCK_RESPONSES: dict[str, dict] = {
    "sort": {
        "reasoning": "Simple single-function task, no decomposition needed",
        "steps": [
            {
                "id": "sort_function",
                "task": "Implement a sorting function",
                "depends_on": [],
                "complexity": "simple",
            }
        ],
    },
    "snake": {
        "reasoning": "Breaking into config, entities, game logic, and main loop for modularity. Snake and food can be built in parallel since they only depend on config.",
        "steps": [
            {
                "id": "config",
                "task": "Game constants (screen size, colors, speed, grid size)",
                "depends_on": [],
                "complexity": "simple",
            },
            {
                "id": "snake",
                "task": "Snake class with body segments, direction, and movement methods",
                "depends_on": ["config"],
                "complexity": "medium",
            },
            {
                "id": "food",
                "task": "Food class with random spawn logic avoiding snake body",
                "depends_on": ["config"],
                "complexity": "simple",
            },
            {
                "id": "collision",
                "task": "Collision detection for walls, self-collision, and food eating",
                "depends_on": ["snake", "food"],
                "complexity": "medium",
            },
            {
                "id": "game_loop",
                "task": "Main game loop with pygame initialization, event handling, rendering, and game over logic",
                "depends_on": ["collision"],
                "complexity": "complex",
            },
        ],
    },
    "calculator": {
        "reasoning": "Medium complexity app with operations, parser, and UI. Operations and parser can be built in parallel.",
        "steps": [
            {
                "id": "operations",
                "task": "Basic math operations (add, subtract, multiply, divide) with error handling",
                "depends_on": [],
                "complexity": "simple",
            },
            {
                "id": "parser",
                "task": "Expression parser to tokenize and parse mathematical expressions",
                "depends_on": [],
                "complexity": "medium",
            },
            {
                "id": "evaluator",
                "task": "Expression evaluator that uses parser and operations with operator precedence",
                "depends_on": ["operations", "parser"],
                "complexity": "medium",
            },
            {
                "id": "calculator_class",
                "task": "Calculator class combining all components with history tracking",
                "depends_on": ["evaluator"],
                "complexity": "medium",
            },
        ],
    },
    "todo": {
        "reasoning": "Todo app needs data model, storage, and CLI interface. Model and storage can be parallel.",
        "steps": [
            {
                "id": "todo_model",
                "task": "Todo item dataclass with id, title, completed status, created_at",
                "depends_on": [],
                "complexity": "simple",
            },
            {
                "id": "storage",
                "task": "JSON file storage for persisting todos with load/save methods",
                "depends_on": [],
                "complexity": "simple",
            },
            {
                "id": "todo_service",
                "task": "TodoService class with CRUD operations using storage",
                "depends_on": ["todo_model", "storage"],
                "complexity": "medium",
            },
            {
                "id": "cli",
                "task": "Command-line interface with argparse for add, list, complete, delete commands",
                "depends_on": ["todo_service"],
                "complexity": "medium",
            },
        ],
    },
    "api": {
        "reasoning": "REST API with models, routes, and error handling. Models come first, then routes.",
        "steps": [
            {
                "id": "models",
                "task": "Pydantic models for request/response schemas",
                "depends_on": [],
                "complexity": "simple",
            },
            {
                "id": "database",
                "task": "In-memory database with CRUD operations",
                "depends_on": ["models"],
                "complexity": "medium",
            },
            {
                "id": "routes",
                "task": "FastAPI routes for GET, POST, PUT, DELETE endpoints",
                "depends_on": ["database"],
                "complexity": "medium",
            },
            {
                "id": "error_handling",
                "task": "Exception handlers and error response formatting",
                "depends_on": ["routes"],
                "complexity": "simple",
            },
        ],
    },
}


def get_mock_plan_response(task: str) -> str:
    """
    Get a mock LLM response for a given task.

    Matches task against known patterns and returns appropriate mock response.
    Falls back to a generic single-step response for unknown tasks.

    Args:
        task: The task description to match.

    Returns:
        JSON string mimicking LLM response format.

    Example:
        >>> response = get_mock_plan_response("Create a snake game")
        >>> data = json.loads(response)
        >>> len(data["steps"])
        5
    """
    task_lower = task.lower()

    # Check for keyword matches
    for keyword, response_data in MOCK_RESPONSES.items():
        if keyword in task_lower:
            return json.dumps(response_data, indent=2)

    # Default fallback for unknown tasks
    fallback = {
        "reasoning": "Single step task, executing directly",
        "steps": [
            {
                "id": "main",
                "task": task,
                "depends_on": [],
                "complexity": "medium",
            }
        ],
    }
    return json.dumps(fallback, indent=2)


def get_mock_plan_response_with_markdown(task: str) -> str:
    """
    Get a mock response wrapped in markdown code block.

    Useful for testing the parser's markdown extraction logic.

    Args:
        task: The task description to match.

    Returns:
        JSON string wrapped in markdown code block.
    """
    json_response = get_mock_plan_response(task)
    return f"```json\n{json_response}\n```"
