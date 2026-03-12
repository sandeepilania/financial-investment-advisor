"""Tool for DuckDuckGo web search via Instant Answer API."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any, Iterable

from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext

from core.loggers import log_tool_call


class WebSearchTool:
    """Tool to query DuckDuckGo for lightweight web results."""

    __name__ = name = "web_search_tool"
    description = "Searches the web using DuckDuckGo Instant Answer API."

    @log_tool_call("web_search_tool")
    def search_web(
        self,
        query: str,
        tool_context: ToolContext,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Search DuckDuckGo and return top results."""
        if not query.strip():
            return []

        params = {
            "q": query,
            "format": "json",
            "no_html": 1,
            "skip_disambig": 1,
        }
        url = "https://api.duckduckgo.com/?" + urllib.parse.urlencode(params)

        with urllib.request.urlopen(url, timeout=20) as response:
            payload = response.read().decode("utf-8")
            data = json.loads(payload)

        results = []
        for item in self._flatten_related_topics(data.get("RelatedTopics", [])):
            title = item.get("Text")
            url = item.get("FirstURL")
            if not title or not url:
                continue
            results.append({"title": title, "url": url, "snippet": title})
            if len(results) >= top_k:
                break

        return results

    def get_tools(self) -> list[FunctionTool]:
        """Return the list of tools provided by this toolset."""
        return [FunctionTool(self.search_web)]

    @staticmethod
    def _flatten_related_topics(items: Iterable[dict[str, Any]]) -> Iterable[dict[str, Any]]:
        for item in items:
            if "Topics" in item:
                yield from WebSearchTool._flatten_related_topics(item.get("Topics", []))
            else:
                yield item
