"""Analyst agent for research tasks."""

from __future__ import annotations

from agents.analyst_agent.prompts import get_analyst_agent_prompt
from core.jpmc_agent import create_jpmc_agent
from core.state import State
from tools.knowledge_search_tool import KnowledgeSearchTool
from tools.web_search_tool import WebSearchTool


def create_analyst_agent(*, name: str = "analyst_agent"):
	"""Create the analyst agent with KB and web search tools."""
	tools = [
		*KnowledgeSearchTool().get_tools(),
		*WebSearchTool().get_tools(),
	]

	return create_jpmc_agent(
		name=name,
		description="Researches market concepts using KB and web search.",
		instruction=get_analyst_agent_prompt,
		tools=tools,
		output_key=State.ANALYST_FINDINGS,
		include_contents="none",
	)
