"""Tool for Tavily web search."""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext

from core.loggers import log_tool_call


class WebSearchTool:
    """Tool to query Tavily for web results."""

    __name__ = name = "web_search_tool"
    description = "Searches the web using the Tavily API."

    @log_tool_call("web_search_tool")
    def search_web(
        self,
        query: str,
        tool_context: ToolContext,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Search Tavily and return top results."""
        if not query.strip():
            return []

        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise RuntimeError("Missing TAVILY_API_KEY")

        payload = json.dumps({
            "api_key": api_key,
            "query": query,
            "max_results": top_k,
        }).encode("utf-8")

        request = urllib.request.Request(
            "https://api.tavily.com/search",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))

        results = []
        for item in data.get("results", []):
            title = item.get("title")
            url = item.get("url")
            snippet = item.get("content") or item.get("snippet")
            if not title or not url:
                continue
            results.append({"title": title, "url": url, "snippet": snippet})
            if len(results) >= top_k:
                break

        return results

    def get_tools(self) -> list[FunctionTool]:
        """Return the list of tools provided by this toolset."""
        return [FunctionTool(self.search_web)]

