"""Tool for searching the local knowledge base."""

from __future__ import annotations

from typing import Any

from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext

from knowledge_store import KnowledgeStore


class KnowledgeSearchTool:
    """Tool to query the local knowledge base."""

    __name__ = name = "knowledge_search_tool"
    description = "Searches the local knowledge base for relevant investment information."

    def __init__(self) -> None:
        self._store = KnowledgeStore()

    def search_kb(
        self,
        query: str,
        tool_context: ToolContext,
        top_k: int = 5,
        filters: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search the knowledge base and return top results."""
        if not self._store.is_ready:
            self._store.ingest()

        return self._store.search(query, top_k=top_k, filters=filters)

    def get_tools(self) -> list[FunctionTool]:
        """Return the list of tools provided by this toolset."""
        return [FunctionTool(self.search_kb)]
