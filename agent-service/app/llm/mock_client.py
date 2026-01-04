"""
Mock LLM Client

Returns fake but valid responses for testing without API calls.
Enable with: USE_MOCK_LLM=true
"""

import asyncio
from app.core.base_llm import BaseLLMClient, LLMResponse


MOCK_RESPONSES = {
    "identify": "CODE_GENERATION",
    "can_handle": "YES",
}

# Task-specific mock code responses
MOCK_CODE_RESPONSES = {
    "snake": '''"""Snake Game - A classic arcade game implementation."""
import random

# Game constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
GRID_SIZE = 20
SNAKE_COLOR = (0, 255, 0)
FOOD_COLOR = (255, 0, 0)
BG_COLOR = (0, 0, 0)

class Snake:
    """Snake entity with movement and growth."""

    def __init__(self):
        self.body = [(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)]
        self.direction = (GRID_SIZE, 0)
        self.grow_pending = False

    def move(self):
        """Move snake in current direction."""
        head_x, head_y = self.body[0]
        dx, dy = self.direction
        new_head = (head_x + dx, head_y + dy)
        self.body.insert(0, new_head)
        if not self.grow_pending:
            self.body.pop()
        self.grow_pending = False

    def grow(self):
        """Mark snake to grow on next move."""
        self.grow_pending = True

    def check_collision(self):
        """Check if snake hit wall or itself."""
        head = self.body[0]
        # Wall collision
        if not (0 <= head[0] < SCREEN_WIDTH and 0 <= head[1] < SCREEN_HEIGHT):
            return True
        # Self collision
        if head in self.body[1:]:
            return True
        return False

class Food:
    """Food that snake can eat to grow."""

    def __init__(self):
        self.position = self.spawn()

    def spawn(self):
        """Spawn food at random grid position."""
        x = random.randint(0, (SCREEN_WIDTH - GRID_SIZE) // GRID_SIZE) * GRID_SIZE
        y = random.randint(0, (SCREEN_HEIGHT - GRID_SIZE) // GRID_SIZE) * GRID_SIZE
        return (x, y)

    def respawn(self):
        """Move food to new random position."""
        self.position = self.spawn()

def game_loop():
    """Main game loop."""
    snake = Snake()
    food = Food()
    score = 0

    print("Snake Game Started!")
    print(f"Snake at: {snake.body[0]}")
    print(f"Food at: {food.position}")

    # Simulate a few moves
    for i in range(5):
        snake.move()
        if snake.body[0] == food.position:
            snake.grow()
            food.respawn()
            score += 10
            print(f"Ate food! Score: {score}")
        if snake.check_collision():
            print(f"Game Over! Final score: {score}")
            break
        print(f"Move {i+1}: Snake head at {snake.body[0]}")

    print(f"Game ended. Final score: {score}")
    return score

if __name__ == "__main__":
    game_loop()
''',

    "calculator": '''"""Calculator - Basic arithmetic operations."""

class Calculator:
    """A simple calculator with memory."""

    def __init__(self):
        self.memory = 0
        self.history = []

    def add(self, a: float, b: float) -> float:
        """Add two numbers."""
        result = a + b
        self._record(f"{a} + {b} = {result}")
        return result

    def subtract(self, a: float, b: float) -> float:
        """Subtract b from a."""
        result = a - b
        self._record(f"{a} - {b} = {result}")
        return result

    def multiply(self, a: float, b: float) -> float:
        """Multiply two numbers."""
        result = a * b
        self._record(f"{a} * {b} = {result}")
        return result

    def divide(self, a: float, b: float) -> float:
        """Divide a by b."""
        if b == 0:
            raise ValueError("Cannot divide by zero")
        result = a / b
        self._record(f"{a} / {b} = {result}")
        return result

    def _record(self, operation: str):
        """Record operation in history."""
        self.history.append(operation)

    def show_history(self):
        """Display calculation history."""
        for op in self.history:
            print(op)

if __name__ == "__main__":
    calc = Calculator()
    print("Calculator Demo:")
    print(f"5 + 3 = {calc.add(5, 3)}")
    print(f"10 - 4 = {calc.subtract(10, 4)}")
    print(f"6 * 7 = {calc.multiply(6, 7)}")
    print(f"20 / 4 = {calc.divide(20, 4)}")
    print("\\nHistory:")
    calc.show_history()
''',

    "todo": '''"""Todo App - Task management system."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Task:
    """A todo task."""
    id: int
    title: str
    completed: bool = False
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

class TodoList:
    """Manage a list of tasks."""

    def __init__(self):
        self.tasks: list[Task] = []
        self._next_id = 1

    def add(self, title: str) -> Task:
        """Add a new task."""
        task = Task(id=self._next_id, title=title)
        self.tasks.append(task)
        self._next_id += 1
        return task

    def complete(self, task_id: int) -> Optional[Task]:
        """Mark a task as completed."""
        for task in self.tasks:
            if task.id == task_id:
                task.completed = True
                return task
        return None

    def delete(self, task_id: int) -> bool:
        """Delete a task."""
        for i, task in enumerate(self.tasks):
            if task.id == task_id:
                self.tasks.pop(i)
                return True
        return False

    def list_all(self) -> list[Task]:
        """Get all tasks."""
        return self.tasks

    def list_pending(self) -> list[Task]:
        """Get incomplete tasks."""
        return [t for t in self.tasks if not t.completed]

if __name__ == "__main__":
    todo = TodoList()

    # Add some tasks
    todo.add("Learn Python")
    todo.add("Build a project")
    todo.add("Write tests")

    print("All tasks:")
    for task in todo.list_all():
        status = "✓" if task.completed else "○"
        print(f"  {status} [{task.id}] {task.title}")

    # Complete a task
    todo.complete(1)
    print("\\nAfter completing task 1:")
    for task in todo.list_all():
        status = "✓" if task.completed else "○"
        print(f"  {status} [{task.id}] {task.title}")

    print(f"\\nPending tasks: {len(todo.list_pending())}")
''',

    "api": '''"""REST API - Simple CRUD endpoints."""
from dataclasses import dataclass, field
from typing import Optional
import json

@dataclass
class User:
    """User model."""
    id: int
    name: str
    email: str

class UserAPI:
    """In-memory user API."""

    def __init__(self):
        self.users: dict[int, User] = {}
        self._next_id = 1

    def create(self, name: str, email: str) -> User:
        """POST /users - Create a new user."""
        user = User(id=self._next_id, name=name, email=email)
        self.users[user.id] = user
        self._next_id += 1
        return user

    def get(self, user_id: int) -> Optional[User]:
        """GET /users/{id} - Get user by ID."""
        return self.users.get(user_id)

    def get_all(self) -> list[User]:
        """GET /users - List all users."""
        return list(self.users.values())

    def update(self, user_id: int, name: str = None, email: str = None) -> Optional[User]:
        """PUT /users/{id} - Update user."""
        user = self.users.get(user_id)
        if user:
            if name:
                user.name = name
            if email:
                user.email = email
        return user

    def delete(self, user_id: int) -> bool:
        """DELETE /users/{id} - Delete user."""
        if user_id in self.users:
            del self.users[user_id]
            return True
        return False

if __name__ == "__main__":
    api = UserAPI()

    # Create users
    user1 = api.create("Alice", "alice@example.com")
    user2 = api.create("Bob", "bob@example.com")
    print(f"Created: {user1}")
    print(f"Created: {user2}")

    # List all
    print(f"\\nAll users: {api.get_all()}")

    # Update
    api.update(1, name="Alice Smith")
    print(f"\\nUpdated user 1: {api.get(1)}")

    # Delete
    api.delete(2)
    print(f"After deleting user 2: {api.get_all()}")
''',

    "fibonacci": '''"""Fibonacci - Calculate fibonacci numbers."""

def fibonacci(n: int) -> int:
    """Calculate the nth fibonacci number."""
    if n < 0:
        raise ValueError("n must be non-negative")
    if n <= 1:
        return n

    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b

def fibonacci_sequence(count: int) -> list[int]:
    """Generate first 'count' fibonacci numbers."""
    return [fibonacci(i) for i in range(count)]

if __name__ == "__main__":
    print("Fibonacci Sequence (first 15 numbers):")
    sequence = fibonacci_sequence(15)
    print(sequence)

    print("\\nIndividual calculations:")
    for n in [0, 1, 5, 10, 20]:
        print(f"fibonacci({n}) = {fibonacci(n)}")
''',

    "default": '''def hello_world(name: str = "World") -> str:
    """Return a greeting message."""
    return f"Hello, {name}!"


if __name__ == "__main__":
    print(hello_world())
    print(hello_world("Developer"))
''',
}


def _get_mock_code(prompt: str) -> str:
    """Get task-specific mock code based on prompt keywords."""
    prompt_lower = prompt.lower()

    if "snake" in prompt_lower:
        return MOCK_CODE_RESPONSES["snake"]
    elif "calculator" in prompt_lower:
        return MOCK_CODE_RESPONSES["calculator"]
    elif "todo" in prompt_lower:
        return MOCK_CODE_RESPONSES["todo"]
    elif "api" in prompt_lower or "crud" in prompt_lower or "rest" in prompt_lower:
        return MOCK_CODE_RESPONSES["api"]
    elif "fibonacci" in prompt_lower or "fib" in prompt_lower:
        return MOCK_CODE_RESPONSES["fibonacci"]

    return MOCK_CODE_RESPONSES["default"]


def _get_planner_response(prompt: str) -> str:
    """Get mock planner response based on task in prompt."""
    # Import here to avoid circular imports
    from app.agents.planner.mock_responses import get_mock_plan_response

    # Extract task from prompt (look for "Task:" line)
    prompt_lower = prompt.lower()
    for line in prompt.split("\n"):
        if line.strip().lower().startswith("task:"):
            task = line.split(":", 1)[1].strip()
            return get_mock_plan_response(task)

    # Fallback: look for keywords
    if "snake" in prompt_lower:
        return get_mock_plan_response("snake game")
    elif "calculator" in prompt_lower:
        return get_mock_plan_response("calculator")
    elif "todo" in prompt_lower:
        return get_mock_plan_response("todo app")
    elif "api" in prompt_lower:
        return get_mock_plan_response("api")

    # Default fallback
    return get_mock_plan_response("unknown task")


class MockLLMClient(BaseLLMClient):
    """Mock LLM client for testing."""

    def __init__(self, latency_ms: float = 100):
        self.latency_ms = latency_ms
        self.call_count = 0  # Track calls for testing

    async def _simulate_latency(self):
        if self.latency_ms > 0:
            await asyncio.sleep(self.latency_ms / 1000)

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        await self._simulate_latency()
        self.call_count += 1

        prompt_lower = prompt.lower()
        system_lower = (system_prompt or "").lower()

        # Check for planner prompts
        if "software architect" in system_lower or "break it into" in prompt_lower:
            content = _get_planner_response(prompt)
        elif "yes or no" in prompt_lower or "can you handle" in prompt_lower:
            content = MOCK_RESPONSES["can_handle"]
        elif "classify" in prompt_lower or "task type" in prompt_lower:
            content = MOCK_RESPONSES["identify"]
        else:
            # Get task-specific mock code
            content = _get_mock_code(prompt)

        prompt_tokens = len(prompt.split())
        completion_tokens = len(content.split())

        return LLMResponse(
            content=content,
            model="mock-llm",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )

    async def generate_with_context(
        self,
        prompt: str,
        context: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        return await self.generate(prompt, system_prompt, temperature, max_tokens)

    def get_model_name(self) -> str:
        return "mock-llm"
