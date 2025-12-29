"""
Logging Utilities for Agent Workflow

Provides structured logging with timing for each LangGraph node.
"""

import logging
import time
from dataclasses import dataclass, field

# Configure logging format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s │ %(levelname)-5s │ %(message)s',
    datefmt='%H:%M:%S'
)

logger = logging.getLogger("code_agent")

@dataclass
class NodeMetrics:
    """Tracks timing for a single node execution."""
    node_name: str
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    duration_ms: float | None = None
    status: str = "running"
    
    def complete(self, status: str = "success"):
        """Mark node as complete and calculate duration."""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = status

@dataclass 
class WorkflowMetrics:
    """Tracks timing for entire workflow (all nodes)."""
    task_id: str
    nodes: list[NodeMetrics] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    
    def start_node(self, node_name: str) -> NodeMetrics:
        """Create and track a new node."""
        node = NodeMetrics(node_name=node_name)
        self.nodes.append(node)
        return node
    
    def complete(self):
        """Mark workflow as complete."""
        self.end_time = time.time()
    
    def total_duration_ms(self) -> float:
        """Total workflow time in milliseconds."""
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0
    
    def slowest_node(self) -> NodeMetrics | None:
        """Find the node that took the longest."""
        completed = [n for n in self.nodes if n.duration_ms]
        if completed:
            return max(completed, key=lambda n: n.duration_ms)
        return None
    
# Storage for workflow metrics (by task_id)
_workflow_metrics: dict[str, WorkflowMetrics] = {}


def get_workflow_metrics(task_id: str) -> WorkflowMetrics:
    """Get or create workflow metrics for a task."""
    if task_id not in _workflow_metrics:
        _workflow_metrics[task_id] = WorkflowMetrics(task_id=task_id)
    return _workflow_metrics[task_id]

def log_node_start(task_id: str, node_name: str, message: str):
    """Log when a node starts processing."""
    metrics = get_workflow_metrics(task_id)
    metrics.start_node(node_name)
    
    # Emoji for each node type
    emoji_map = {
        "identify": "🔍",
        "execute": "⚡",
        "evaluate": "✅",
    }
    emoji = emoji_map.get(node_name, "📌")
    
    logger.info(f"{emoji} [{node_name.upper():^10}] {message}")


def log_node_complete(task_id: str, node_name: str, message: str, status: str = "success"):
    """Log when a node completes."""
    metrics = get_workflow_metrics(task_id)
    
    # Find and complete the most recent node with this name
    for node in reversed(metrics.nodes):
        if node.node_name == node_name and node.end_time is None:
            node.complete(status)
            logger.info(f"   └── Done ({node.duration_ms:.0f}ms) - {message}")
            break

def log_workflow_complete(task_id: str):
    """Log workflow completion with summary."""
    metrics = get_workflow_metrics(task_id)
    metrics.complete()
    
    # Build summary
    lines = [
        f"\n{'='*50}",
        f"📊 WORKFLOW COMPLETE - Task {task_id[:8]}...",
        f"{'='*50}",
        f"Total Duration: {metrics.total_duration_ms():.0f}ms",
        f"",
        f"Node Breakdown:",
    ]
    
    for node in metrics.nodes:
        if node.duration_ms:
            bar_length = int(node.duration_ms / 100)  # 1 char per 100ms
            bar = "█" * min(bar_length, 30)
            lines.append(f"  {node.node_name:15} │ {node.duration_ms:6.0f}ms │ {bar}")
    
    slowest = metrics.slowest_node()
    if slowest:
        lines.append(f"")
        lines.append(f"🐢 Slowest: {slowest.node_name} ({slowest.duration_ms:.0f}ms)")
    
    lines.append(f"{'='*50}\n")
    
    # Print the summary
    print("\n".join(lines))


def log_retry(task_id: str, attempt: int, max_attempts: int, reason: str):
    """Log retry attempts."""
    logger.warning(f"🔄 [RETRY {attempt}/{max_attempts}] {reason}")


def log_error(task_id: str, node_name: str, error: str):
    """Log errors."""
    logger.error(f"❌ [{node_name.upper()}] Error: {error}")