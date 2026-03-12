"""Tool for searching the local knowledge base."""

from __future__ import annotations

from typing import Any

from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext

from core.loggers import log_tool_call
from knowledge_store import KnowledgeStore


class KnowledgeSearchTool:
    """Tool to query the local knowledge base."""

    __name__ = name = "knowledge_search_tool"
    description = "Searches the local knowledge base for relevant investment information."

    def __init__(self) -> None:
        self._store = KnowledgeStore()

    @log_tool_call("knowledge_search_tool")
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

        raw_results = self._store.search(query, top_k=top_k, filters=filters)
        results: list[dict[str, Any]] = []
        for item in raw_results:
            title = item.get("title") or item.get("doc_id") or "KB Result"
            doc_id = item.get("doc_id")
            snippet = item.get("content") or item.get("text_for_embedding") or ""
            category = item.get("category")
            citations = item.get("citations") or []
            url = citations[0] if citations else f"kb://{doc_id}" if doc_id else "kb://unknown"
            results.append(
                {
                    "title": title,
                    "url": url,
                    "snippet": snippet,
                    "source_type": "KB",
                    "doc_id": doc_id,
                    "category": category,
                }
            )

        return results

    def get_tools(self) -> list[FunctionTool]:
        """Return the list of tools provided by this toolset."""
        return [FunctionTool(self.search_kb)]
