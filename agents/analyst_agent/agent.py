"""Analyst agent for research tasks."""

from __future__ import annotations

import json

from agents.analyst_agent.prompts import get_analyst_agent_prompt
from google.adk.agents.callback_context import CallbackContext
from google.genai import types
from pydantic import BaseModel

from core.jpmc_agent import create_jpmc_agent
from core.state import State
from schemas.analyst_findings import AnalystFindings
from tools.knowledge_search_tool import KnowledgeSearchTool
from tools.web_search_tool import WebSearchTool


def _analyst_guard(callback_context: CallbackContext) -> types.Content | None:
	state = callback_context.state
	existing = state.get(State.ANALYST_FINDINGS)
	if existing:
		if isinstance(existing, dict):
			payload = dict(existing)
			payload.setdefault("assumptions", [])
			payload.setdefault("missing_data", [])
		else:
			payload = {
				"findings": [{"detail": str(existing), "sources": []}],
				"assumptions": [],
				"missing_data": [],
			}
		return types.Content(
			role="assistant",
			parts=[types.Part(text=json.dumps(payload))],
		)
	return None


def _capture_analyst_findings(callback_context: CallbackContext) -> None:
	state = callback_context.state
	if state.get(State.ANALYST_FINDINGS):
		return

	response = getattr(callback_context, "response", None)
	output = getattr(callback_context, "output", None)
	content = response or output

	if isinstance(content, BaseModel):
		state[State.ANALYST_FINDINGS] = content.model_dump()
		return
	if isinstance(content, dict):
		state[State.ANALYST_FINDINGS] = content
		return

	text = None

	if isinstance(content, str):
		text = content
	else:
		parts = getattr(content, "parts", None) if content else None
		if parts:
			texts = [getattr(part, "text", "") for part in parts if getattr(part, "text", None)]
			text = "\n".join(texts) if texts else None

	if text:
		state[State.ANALYST_FINDINGS] = text


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
		output_schema=AnalystFindings,
		before_agent_callback=_analyst_guard,
		after_agent_callback=[_capture_analyst_findings],
	)
