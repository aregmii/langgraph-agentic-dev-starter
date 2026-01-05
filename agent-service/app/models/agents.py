"""Agent types, protocols, and team management.

This module defines the agent abstraction layer:
- AgentType: Enum of available agent types
- Agent: Protocol that all agents must implement
- AgentInfo: Metadata about agent capabilities
- AgentTeam: Container for agent instances assigned to a Manager
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable, Any


class AgentType(Enum):
    """Types of agents available in the system."""

    BUILDER = "builder"
    REVIEWER = "reviewer"
    DOCGEN = "docgen"


@runtime_checkable
class Agent(Protocol):
    """Protocol that all agents must implement.

    Each agent has:
    - agent_type: What kind of agent this is
    - agent_id: Unique identifier (e.g., "builder-1", "builder-2")
    - execute(): Async method to perform the agent's work
    """

    agent_type: AgentType
    agent_id: str

    async def execute(self, task: Any) -> Any:
        """Execute the agent's task."""
        ...


@dataclass
class AgentInfo:
    """Metadata about an agent type (not instance).

    Used by Manager to understand what each agent type can do.
    """

    agent_type: AgentType
    name: str
    description: str
    capabilities: list[str]


# Registry of agent type metadata
AGENT_REGISTRY: dict[AgentType, AgentInfo] = {
    AgentType.BUILDER: AgentInfo(
        agent_type=AgentType.BUILDER,
        name="SoftwareBuilderAgent",
        description="Generates code and tests for a single step",
        capabilities=["code_generation", "test_generation", "code_fixing"],
    ),
    AgentType.REVIEWER: AgentInfo(
        agent_type=AgentType.REVIEWER,
        name="SoftwareReviewerAgent",
        description="Runs tests and reviews code quality",
        capabilities=["test_execution", "code_review", "feedback"],
    ),
    AgentType.DOCGEN: AgentInfo(
        agent_type=AgentType.DOCGEN,
        name="DocumentationGeneratorAgent",
        description="Adds docstrings and generates README",
        capabilities=["docstrings", "readme_generation", "comments"],
    ),
}


@dataclass
class AgentTeam:
    """A team of agent instances that a Manager can delegate work to.

    Currently supports 1 instance per type, but architecture ready
    for multiple instances (e.g., 3 builders for true parallelism).

    Example:
        >>> team = AgentTeam()
        >>> team.add_agent(builder_instance)
        >>> team.add_agent(reviewer_instance)
        >>> team.get_team_summary()
        {'builders': 1, 'reviewers': 1, 'docgens': 0}
    """

    builders: list[Agent] = field(default_factory=list)
    reviewers: list[Agent] = field(default_factory=list)
    docgens: list[Agent] = field(default_factory=list)

    def get_agents(self, agent_type: AgentType) -> list[Agent]:
        """Get all agents of a specific type."""
        match agent_type:
            case AgentType.BUILDER:
                return self.builders
            case AgentType.REVIEWER:
                return self.reviewers
            case AgentType.DOCGEN:
                return self.docgens
        return []

    def get_agent(self, agent_type: AgentType, index: int = 0) -> Agent | None:
        """Get a specific agent instance. Defaults to first available."""
        agents = self.get_agents(agent_type)
        return agents[index] if index < len(agents) else None

    def get_available_types(self) -> list[AgentType]:
        """Get list of agent types that have at least one instance."""
        available = []
        if self.builders:
            available.append(AgentType.BUILDER)
        if self.reviewers:
            available.append(AgentType.REVIEWER)
        if self.docgens:
            available.append(AgentType.DOCGEN)
        return available

    def get_team_summary(self) -> str:
        """Get human-readable summary of team composition."""
        return f"{len(self.builders)} builder(s), {len(self.reviewers)} reviewer(s), {len(self.docgens)} docgen(s)"

    def add_agent(self, agent: Agent) -> None:
        """Add an agent instance to the team."""
        match agent.agent_type:
            case AgentType.BUILDER:
                self.builders.append(agent)
            case AgentType.REVIEWER:
                self.reviewers.append(agent)
            case AgentType.DOCGEN:
                self.docgens.append(agent)

    def has_minimum_team(self) -> bool:
        """Check if team has at least one of each required agent type."""
        return bool(self.builders and self.reviewers and self.docgens)
