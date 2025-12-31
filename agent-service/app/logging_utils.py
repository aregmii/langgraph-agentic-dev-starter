"""
Logging Utilities for Agent Workflow

Clear, traceable logs with agent names for multi-agent systems.
Every line prefixed with request ID for concurrent request filtering.
"""

import logging
import sys
import time
from dataclasses import dataclass, field

# Suppress noisy uvicorn/httpx logs
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Configure our logger
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
)
logger = logging.getLogger("code_agent")


def short_id(task_id: str) -> str:
    """Create short request ID for logs."""
    return f"req-{task_id[:8]}"


def log(task_id: str, message: str):
    """Log a message with request ID prefix."""
    print(f"[{short_id(task_id)}] {message}", flush=True)


def log_request_start(task_id: str, description: str, context: str | None, mock_mode: bool):
    """Log when a new request arrives."""
    rid = short_id(task_id)
    mode = "MOCK (no API calls)" if mock_mode else "REAL (using Grok API)"
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
