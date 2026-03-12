"""Tool for setting analyst research sources in shared state."""

from __future__ import annotations

from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext

from core.state import State


ResearchModeToolResult = dict[str, bool | list[str]]


class ResearchModeTool:
    """Tool to set analyst research sources in state."""

    __name__ = name = "research_mode_tool"
    description = "Sets State.ANALYST_RESEARCH_MODE as a list of research sources."

    def set_research_mode(
        self,
        modes: list[str],
        tool_context: ToolContext,
    ) -> ResearchModeToolResult:
        """Set the analyst research mode list in state."""
        tool_context.state[State.ANALYST_RESEARCH_MODE] = modes
        return {"success": True, "modes": modes}

    def get_tools(self) -> list[FunctionTool]:
        """Return the list of tools provided by this toolset."""
        return [FunctionTool(self.set_research_mode)]
