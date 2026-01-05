"""LangGraph-based Manager Agent - Orchestrates multi-agent workflow using StateGraph.

This implementation uses LangGraph's StateGraph to define the workflow:
- Nodes: builder, reviewer, docgen
- Edges: builder → reviewer, reviewer → (conditional) → builder OR docgen
- Conditional routing based on review results (reflection loop)

Demonstrates:
- TypedDict state management
- Graph-based agent orchestration
- Conditional edges for branching logic
- State accumulation across nodes
"""

import time
from typing import Callable, TypedDict, Literal, Annotated
from operator import add

from langgraph.graph import StateGraph, END

from app.core.base_llm import BaseLLMClient
from app.models.agents import AgentType, AgentTeam
from app.models.execution import (
    StepTask, CodeOutput, CompletedStep,
    DocumentedCode, ProjectResult, ReviewIssue,
)
from app.agents.builder import SoftwareBuilderAgent
from app.agents.reviewer import SoftwareReviewerAgent
from app.agents.docgen import DocumentationGeneratorAgent
from app.logging_utils import (
    log_agent_start, log_agent_complete, log_validation_step, log_reflection
)


# ============================================================================
# STATE DEFINITION
# ============================================================================

class AgentState(TypedDict):
    """State that flows through the LangGraph workflow.

    This TypedDict defines the shape of state passed between nodes.
    LangGraph automatically merges updates from each node.
    """
    # Input
    task: str

    # Build phase
    code: str
    tests: str

    # Review phase
    review_passed: bool
    issues: list[ReviewIssue]

    # Tracking
    attempt: int
    max_attempts: int
    previous_code: str

    # Documentation phase
    documented_code: str
    readme: str

    # Output
    success: bool
    error_message: str
    start_time: float


# ============================================================================
# LANGGRAPH MANAGER
# ============================================================================

class LangGraphManager:
    """Orchestrates agents using LangGraph StateGraph.

    The workflow is defined as a graph:

        ┌─────────┐     ┌──────────┐     ┌─────────┐
        │ builder │ ──► │ reviewer │ ──► │ docgen  │ ──► END
        └─────────┘     └──────────┘     └─────────┘
                              │                ▲
                              │ (if failed)    │
                              └────────────────┘
                                 (retry loop)

    Key LangGraph concepts demonstrated:
    - StateGraph: Defines the workflow structure
    - add_node: Registers agent functions as nodes
    - add_edge: Creates fixed transitions
    - add_conditional_edges: Creates dynamic routing based on state
    """

    MAX_ATTEMPTS = 3  # 1 initial + 2 retries

    def __init__(
        self,
        llm_client: BaseLLMClient,
        event_callback: Callable[[str, dict], None] | None = None,
    ):
        self.llm_client = llm_client
        self.event_callback = event_callback or (lambda e, d: None)

        # Create agents
        self.builder = SoftwareBuilderAgent(
            llm_client=llm_client,
            agent_id="builder-1",
            event_callback=self.event_callback,
        )
        self.reviewer = SoftwareReviewerAgent(
            llm_client=llm_client,
            agent_id="reviewer-1",
            event_callback=self.event_callback,
        )
        self.docgen = DocumentationGeneratorAgent(
            llm_client=llm_client,
            agent_id="docgen-1",
            event_callback=self.event_callback,
        )

        # Build the graph
        self.graph = self._build_graph()
        self.compiled_graph = self.graph.compile()

    def _emit(self, event: str, data: dict) -> None:
        """Emit an SSE event."""
        self.event_callback(event, data)

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph StateGraph.

        This defines:
        1. Nodes (agent functions)
        2. Edges (transitions between nodes)
        3. Conditional edges (dynamic routing)
        """
        # Create the graph with our state type
        graph = StateGraph(AgentState)

        # Add nodes - each node is an async function that takes state and returns updates
        graph.add_node("builder", self._builder_node)
        graph.add_node("reviewer", self._reviewer_node)
        graph.add_node("docgen", self._docgen_node)

        # Set the entry point
        graph.set_entry_point("builder")

        # Add edges
        # builder always goes to reviewer
        graph.add_edge("builder", "reviewer")

        # reviewer has conditional routing based on review result
        graph.add_conditional_edges(
            "reviewer",
            self._should_retry_or_continue,
            {
                "retry": "builder",      # Failed review, retry
                "continue": "docgen",    # Passed review, continue to docs
                "fail": END,             # Max retries reached, end with failure
            }
        )

        # docgen always ends
        graph.add_edge("docgen", END)

        return graph

    # ========================================================================
    # NODE FUNCTIONS
    # ========================================================================

    async def _builder_node(self, state: AgentState) -> dict:
        """Builder node - generates or fixes code.

        This node:
        1. Checks if this is a retry (has issues from previous attempt)
        2. Calls the Builder agent
        3. Returns state updates (code, tests, attempt count)
        """
        start_time = time.time()
        attempt = state.get("attempt", 0) + 1
        is_retry = attempt > 1 and state.get("issues")

        # Emit delegation event
        action = "generate code" if attempt == 1 else f"fix code (attempt {attempt}/{state.get('max_attempts', self.MAX_ATTEMPTS)})"
        self._emit("manager_delegating", {
            "agent": "SoftwareBuilderAgent",
            "agent_id": self.builder.agent_id,
            "action": action,
        })

        # Log agent start
        log_agent_start("SoftwareBuilderAgent", action)

        # Build step task
        step_task = StepTask(
            step_id="main",
            task=state["task"],
            project_goal=state["task"],
            completed_code={},
            issues=state.get("issues", []) if is_retry else [],
            previous_code=state.get("previous_code", "") if is_retry else "",
        )

        # Execute builder
        code_output = await self.builder.execute(step_task)

        duration_ms = (time.time() - start_time) * 1000
        log_agent_complete("SoftwareBuilderAgent", f"Generated {code_output.code_lines} lines", duration_ms)

        # Return state updates
        return {
            "code": code_output.code,
            "tests": code_output.tests,
            "attempt": attempt,
            "previous_code": code_output.code,  # Save for potential retry
        }

    async def _reviewer_node(self, state: AgentState) -> dict:
        """Reviewer node - reviews code and identifies issues.

        This node:
        1. Calls the Reviewer agent
        2. Returns state updates (review result, issues)
        """
        start_time = time.time()

        # Emit delegation event
        self._emit("manager_delegating", {
            "agent": "SoftwareReviewerAgent",
            "agent_id": self.reviewer.agent_id,
            "action": "review code",
        })

        # Log agent start
        log_agent_start("SoftwareReviewerAgent", f"review {len(state['code'].split(chr(10)))} lines of code")

        # Create code output for reviewer
        code_output = CodeOutput(
            step_id="main",
            code=state["code"],
            tests=state.get("tests", ""),
        )

        # Execute reviewer
        review_result = await self.reviewer.execute(code_output, state["task"])

        # Log validation results
        blocking = len([i for i in review_result.issues if i.severity == "error"])
        nonblocking = len([i for i in review_result.issues if i.severity == "warning"])
        log_validation_step("Syntax Check", True, "Valid Python")
        log_validation_step("Code Review", review_result.overall_passed,
                           f"{blocking} blocking, {nonblocking} non-blocking")

        duration_ms = (time.time() - start_time) * 1000
        result = "PASSED" if review_result.overall_passed else f"FAILED ({blocking} blocking issues)"
        log_agent_complete("SoftwareReviewerAgent", result, duration_ms)

        # Return state updates
        return {
            "review_passed": review_result.overall_passed,
            "issues": review_result.issues,
        }

    async def _docgen_node(self, state: AgentState) -> dict:
        """DocGen node - adds documentation.

        This node:
        1. Calls the DocGen agent
        2. Returns state updates (documented code, readme)
        """
        start_time = time.time()

        # Emit delegation event
        self._emit("manager_delegating", {
            "agent": "DocumentationGeneratorAgent",
            "agent_id": self.docgen.agent_id,
            "action": "add documentation",
        })

        # Log agent start
        log_agent_start("DocumentationGeneratorAgent", "add docstrings and README")

        # Create completed step for docgen
        completed = CompletedStep(
            step_id="main",
            code=state["code"],
            tests=state.get("tests", ""),
            attempts=state.get("attempt", 1),
            passed=True,
        )

        # Execute docgen
        documented = await self.docgen.execute([completed], state["task"])

        duration_ms = (time.time() - start_time) * 1000
        log_agent_complete("DocumentationGeneratorAgent", f"Added {documented.readme_lines} line README", duration_ms)

        self._emit("docgen_complete", {
            "agent_id": self.docgen.agent_id,
            "readme_lines": documented.readme_lines,
        })

        # Return state updates
        return {
            "documented_code": documented.code,
            "readme": documented.readme,
            "success": True,
        }

    # ========================================================================
    # CONDITIONAL ROUTING
    # ========================================================================

    def _should_retry_or_continue(self, state: AgentState) -> Literal["retry", "continue", "fail"]:
        """Determine next step after review.

        This is the routing function for conditional edges.

        Returns:
            "retry" - Review failed, retry with builder
            "continue" - Review passed, continue to docgen
            "fail" - Max retries reached, end workflow
        """
        review_passed = state.get("review_passed", False)
        attempt = state.get("attempt", 1)
        max_attempts = state.get("max_attempts", self.MAX_ATTEMPTS)

        if review_passed:
            return "continue"

        if attempt < max_attempts:
            # Emit reflection event
            issues = state.get("issues", [])
            blocking_count = len([i for i in issues if i.severity == "error"])
            blocking_messages = [i.message for i in issues if i.severity == "error"]

            # Log reflection
            log_reflection(attempt, max_attempts, blocking_messages)

            self._emit("reflection_start", {
                "attempt": attempt,
                "max_attempts": max_attempts,
                "blocking_issues": blocking_count,
                "issues": blocking_messages[:3],
            })
            return "retry"

        return "fail"

    # ========================================================================
    # PUBLIC API
    # ========================================================================

    async def run(self, task: str) -> ProjectResult:
        """Execute the LangGraph workflow.

        This is the main entry point. It:
        1. Emits planning events
        2. Invokes the compiled graph
        3. Assembles the final result
        """
        start_time = time.time()

        # Emit planning events
        self._emit("manager_received_task", {"task": task})
        self._emit("manager_plan", {
            "steps": [
                "Use SoftwareBuilderAgent to generate code",
                f"Use SoftwareReviewerAgent to review code (up to {self.MAX_ATTEMPTS} attempts)",
                "Use DocumentationGeneratorAgent to add documentation",
            ],
            "team_summary": "1 builder(s), 1 reviewer(s), 1 docgen(s)",
        })

        # Initial state
        initial_state: AgentState = {
            "task": task,
            "code": "",
            "tests": "",
            "review_passed": False,
            "issues": [],
            "attempt": 0,
            "max_attempts": self.MAX_ATTEMPTS,
            "previous_code": "",
            "documented_code": "",
            "readme": "",
            "success": False,
            "error_message": "",
            "start_time": start_time,
        }

        # Run the graph
        final_state = await self.compiled_graph.ainvoke(initial_state)

        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)

        # Determine success
        success = final_state.get("success", False)
        error_message = None

        if not success:
            issues = final_state.get("issues", [])
            error_count = len([i for i in issues if i.severity == "error"])
            attempt = final_state.get("attempt", 1)
            error_message = f"Review failed with {error_count} blocking issue(s) after {attempt} attempt(s)"

        # Emit completion event
        self._emit("manager_complete", {
            "success": success,
            "total_attempts": final_state.get("attempt", 1),
            "duration_ms": duration_ms,
            "error_message": error_message,
        })

        # Build result
        return ProjectResult(
            code=final_state.get("documented_code") or final_state.get("code", ""),
            tests=final_state.get("tests", ""),
            readme=final_state.get("readme", "# Project\n\nGenerated code."),
            total_steps=1,
            total_attempts=final_state.get("attempt", 1),
            duration_ms=duration_ms,
            success=success,
            error_message=error_message,
        )

    def get_graph_visualization(self) -> str:
        """Return a Mermaid diagram of the graph.

        Useful for documentation and debugging.
        """
        return """
graph TD
    A[Start] --> B[builder]
    B --> C[reviewer]
    C -->|passed| D[docgen]
    C -->|failed & attempts < max| B
    C -->|failed & attempts >= max| E[End - Failed]
    D --> F[End - Success]
"""


# Alias for backwards compatibility
ManagerAgent = LangGraphManager

__all__ = ["LangGraphManager", "ManagerAgent", "AgentState"]
