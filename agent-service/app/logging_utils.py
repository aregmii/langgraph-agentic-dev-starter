"""
Logging Utilities for Agent Workflow

Clear, traceable logs with agent names for multi-agent systems.
Every line prefixed with request ID for concurrent request filtering.
"""

import logging
import sys
import time
import textwrap
from dataclasses import dataclass, field
from contextvars import ContextVar

# Suppress noisy uvicorn/httpx logs
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Configure our logger
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
)
logger = logging.getLogger("code_agent")

# Context variable to track current request ID (thread-safe for async)
_current_request_id: ContextVar[str | None] = ContextVar('current_request_id', default=None)


def set_request_id(task_id: str):
    """Set the current request ID for this async context."""
    _current_request_id.set(task_id)


def get_request_id() -> str | None:
    """Get the current request ID."""
    return _current_request_id.get()


def short_id(task_id: str) -> str:
    """Create short request ID for logs."""
    return f"req-{task_id[:8]}"


def log(task_id: str, message: str):
    """Log a message with request ID prefix."""
    print(f"[{short_id(task_id)}] {message}", flush=True)


def _truncate(text: str, max_lines: int = 8, max_chars: int = 400) -> str:
    """Truncate text for logging."""
    lines = text.split('\n')
    if len(lines) > max_lines:
        text = '\n'.join(lines[:max_lines]) + f'\n... ({len(lines) - max_lines} more lines)'
    if len(text) > max_chars:
        text = text[:max_chars] + f'... ({len(text) - max_chars} more chars)'
    return text


def _indent(text: str, prefix: str = "    │ ") -> str:
    """Indent text for nested log output."""
    return '\n'.join(prefix + line for line in text.split('\n'))


def log_request_start(task_id: str, description: str, context: str | None, mock_mode: bool):
    """Log when a new request arrives."""
    import os
    set_request_id(task_id)  # Set for async context
    rid = short_id(task_id)
    if mock_mode:
        mode = "MOCK (no API calls)"
    else:
        model = os.getenv("OPENROUTER_MODEL", "unknown")
        mode = f"REAL (OpenRouter: {model})"
    desc = description[:60] + "..." if len(description) > 60 else description
    ctx = f'"{context[:40]}..."' if context else "None"

    print(f"[{rid}] {'═' * 66}", flush=True)
    print(f"[{rid}] 🆕 NEW REQUEST", flush=True)
    print(f"[{rid}] {'─' * 66}", flush=True)
    print(f"[{rid}] 📝 Task: \"{desc}\"", flush=True)
    print(f"[{rid}] 📎 Context: {ctx}", flush=True)
    print(f"[{rid}] 🤖 Mode: {mode}", flush=True)
    print(f"[{rid}] {'─' * 66}", flush=True)
    print(f"[{rid}]", flush=True)


# Human-readable step descriptions: (action, method)
STEP_DESCRIPTIONS = {
    "identify": ("Classifying task type", "using LLM"),
    "execute": ("Generating code", "using LLM"),
    "evaluate": ("Validating syntax", "using AST parser"),
}


def log_agent_step_start(task_id: str, agent_name: str, step_name: str, detail: str = ""):
    """Log when an agent starts a step."""
    rid = short_id(task_id)
    desc, method = STEP_DESCRIPTIONS.get(step_name, (step_name, ""))
    action = f"{desc} {method}".strip()
    if detail:
        action = detail
    print(f"[{rid}] → [{agent_name}] {action}...", flush=True)


def log_agent_step_complete(task_id: str, duration_ms: float, result: str):
    """Log when an agent step completes."""
    rid = short_id(task_id)
    print(f"[{rid}] ✓ Done ({duration_ms:.0f}ms) → {result}", flush=True)
    print(f"[{rid}]", flush=True)


def log_agent_step_failed(task_id: str, duration_ms: float, error: str):
    """Log when an agent step fails."""
    rid = short_id(task_id)
    print(f"[{rid}] ✗ Failed ({duration_ms:.0f}ms) → {error}", flush=True)
    print(f"[{rid}]", flush=True)


def log_retry(task_id: str, agent_name: str, attempt: int, max_attempts: int, reason: str):
    """Log a retry attempt."""
    rid = short_id(task_id)
    print(f"[{rid}] 🔄 [{agent_name}] Retrying ({attempt}/{max_attempts}): {reason}", flush=True)
    print(f"[{rid}]", flush=True)


def log_request_complete(task_id: str, total_ms: float, status: str, code_length: int):
    """Log when a request completes successfully."""
    rid = short_id(task_id)
    print(f"[{rid}] {'═' * 66}", flush=True)
    print(f"[{rid}] ✅ COMPLETE | {total_ms:.0f}ms total | {code_length} chars generated", flush=True)
    print(f"[{rid}] {'═' * 66}", flush=True)
    print(flush=True)


def log_request_failed(task_id: str, total_ms: float, error: str):
    """Log when a request fails."""
    rid = short_id(task_id)
    error_short = error[:50] + "..." if len(error) > 50 else error
    print(f"[{rid}] {'═' * 66}", flush=True)
    print(f"[{rid}] ❌ FAILED | {total_ms:.0f}ms | {error_short}", flush=True)
    print(f"[{rid}] {'═' * 66}", flush=True)
    print(flush=True)


# ============================================================================
# DETAILED AGENT LOGGING
# ============================================================================

def log_agent_start(agent_name: str, action: str):
    """Log when an agent starts working."""
    task_id = get_request_id()
    if not task_id:
        return
    rid = short_id(task_id)
    print(f"[{rid}]", flush=True)
    print(f"[{rid}] ┌─ 🤖 {agent_name}", flush=True)
    print(f"[{rid}] │  Action: {action}", flush=True)


def log_agent_complete(agent_name: str, result: str, duration_ms: float):
    """Log when an agent completes."""
    task_id = get_request_id()
    if not task_id:
        return
    rid = short_id(task_id)
    print(f"[{rid}] │  Result: {result}", flush=True)
    print(f"[{rid}] └─ ✅ Done ({duration_ms:.0f}ms)", flush=True)


def log_llm_request(agent_name: str, purpose: str, prompt_preview: str, system_preview: str | None = None):
    """Log an LLM request with prompt preview."""
    task_id = get_request_id()
    if not task_id:
        return
    rid = short_id(task_id)

    print(f"[{rid}] │", flush=True)
    print(f"[{rid}] │  📤 LLM Request: {purpose}", flush=True)

    if system_preview:
        sys_short = _truncate(system_preview, max_lines=3, max_chars=150)
        for line in sys_short.split('\n'):
            print(f"[{rid}] │     [system] {line}", flush=True)

    prompt_short = _truncate(prompt_preview, max_lines=5, max_chars=300)
    for line in prompt_short.split('\n'):
        print(f"[{rid}] │     [prompt] {line}", flush=True)


def log_llm_response(agent_name: str, response_preview: str, tokens: int, duration_ms: float):
    """Log an LLM response with preview."""
    task_id = get_request_id()
    if not task_id:
        return
    rid = short_id(task_id)

    print(f"[{rid}] │  📥 LLM Response ({tokens} tokens, {duration_ms:.0f}ms):", flush=True)
    response_short = _truncate(response_preview, max_lines=6, max_chars=400)
    for line in response_short.split('\n'):
        print(f"[{rid}] │     {line}", flush=True)


def log_validation_step(step_name: str, passed: bool, message: str):
    """Log a validation step result."""
    task_id = get_request_id()
    if not task_id:
        return
    rid = short_id(task_id)
    icon = "✅" if passed else "❌"
    print(f"[{rid}] │  {icon} {step_name}: {message}", flush=True)


def log_reflection(attempt: int, max_attempts: int, issues: list[str]):
    """Log when reflection/retry happens."""
    task_id = get_request_id()
    if not task_id:
        return
    rid = short_id(task_id)
    print(f"[{rid}]", flush=True)
    print(f"[{rid}] ┌─ 🔄 REFLECTION (attempt {attempt}/{max_attempts})", flush=True)
    for issue in issues[:3]:
        print(f"[{rid}] │  • {issue[:60]}", flush=True)
    if len(issues) > 3:
        print(f"[{rid}] │  ... and {len(issues) - 3} more issues", flush=True)
    print(f"[{rid}] └─", flush=True)


# Legacy no-ops for backward compatibility
def log_node_start(task_id: str, node_name: str, message: str):
    pass

def log_node_complete(task_id: str, node_name: str, message: str, status: str = "success"):
    pass

def log_workflow_complete(task_id: str):
    pass

def log_error(task_id: str, node_name: str, error: str):
    pass


# Metrics classes for backward compatibility
@dataclass
class NodeMetrics:
    node_name: str
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    duration_ms: float | None = None
    status: str = "running"

    def complete(self, status: str = "success"):
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = status


@dataclass
class WorkflowMetrics:
    task_id: str
    nodes: list[NodeMetrics] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None

    def start_node(self, node_name: str) -> NodeMetrics:
        node = NodeMetrics(node_name=node_name)
        self.nodes.append(node)
        return node

    def complete(self):
        self.end_time = time.time()

    def total_duration_ms(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0


_workflow_metrics: dict[str, WorkflowMetrics] = {}

def get_workflow_metrics(task_id: str) -> WorkflowMetrics:
    if task_id not in _workflow_metrics:
        _workflow_metrics[task_id] = WorkflowMetrics(task_id=task_id)
    return _workflow_metrics[task_id]
