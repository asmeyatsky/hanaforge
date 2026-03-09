"""AgentToolRegistry — central registry mapping tool names to implementations."""

from __future__ import annotations

import logging

from domain.ports.agent_ports import AgentToolPort
from domain.value_objects.agent_types import AgentTool

logger = logging.getLogger(__name__)


class AgentToolRegistry:
    """Registers available agent tools by name and provides schema descriptors.

    Tools are registered once at startup and looked up by name during agent
    execution.  The registry also generates the tool-schema list required
    by the Claude tool-use API.
    """

    def __init__(self) -> None:
        self._tools: dict[str, AgentToolPort] = {}

    def register(self, tool: AgentToolPort) -> None:
        """Register a tool implementation under its declared name."""
        if tool.name in self._tools:
            logger.warning("Overwriting existing tool registration: %s", tool.name)
        self._tools[tool.name] = tool
        logger.info("Registered agent tool: %s", tool.name)

    def register_many(self, tools: list[AgentToolPort]) -> None:
        """Register multiple tools at once."""
        for tool in tools:
            self.register(tool)

    def get(self, name: str) -> AgentToolPort | None:
        """Look up a tool by name, returning None if not found."""
        return self._tools.get(name)

    def get_or_raise(self, name: str) -> AgentToolPort:
        """Look up a tool by name, raising KeyError if not found."""
        tool = self._tools.get(name)
        if tool is None:
            raise KeyError(
                f"Agent tool '{name}' not registered. "
                f"Available: {', '.join(sorted(self._tools.keys()))}"
            )
        return tool

    def list_names(self) -> list[str]:
        """Return all registered tool names."""
        return sorted(self._tools.keys())

    def get_tool_schemas(self, names: list[str] | None = None) -> list[AgentTool]:
        """Build AgentTool schema descriptors for the Claude API.

        If *names* is provided, only include the specified subset.
        Otherwise return schemas for all registered tools.
        """
        tools_to_include = (
            {n: t for n, t in self._tools.items() if n in names}
            if names is not None
            else self._tools
        )
        return [
            AgentTool(
                name=tool.name,
                description=tool.description,
                input_schema=getattr(tool, "input_schema", {}),
            )
            for tool in tools_to_include.values()
        ]

    async def execute(self, name: str, params: dict) -> dict:
        """Look up and execute a tool by name."""
        tool = self.get_or_raise(name)
        return await tool.execute(params)
