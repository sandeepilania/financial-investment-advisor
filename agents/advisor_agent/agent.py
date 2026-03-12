"""Advisor agent construction and validation callbacks."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
import json
from typing import Any

from google.adk.agents.base_agent import AfterAgentCallback, BeforeAgentCallback
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps.app import App
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types
from pydantic import BaseModel, ValidationError

from core.adk_plugins import StateSerializationPlugin, TokenTracingPlugin
from core.jpmc_agent import create_jpmc_agent
from core.state import State
from agents.advisor_agent.prompts import get_advisor_agent_prompt
from agents.analyst_agent.agent import create_analyst_agent
from agents.client_agent.agent import generate_profile, respond_to_recommendation
from schemas.advisor_recommendation import AdvisorRecommendation
from tools.research_mode_tool import ResearchModeTool
from tools.todo_tool import TodoTool

def _missing_required_state(state: Mapping[str, Any]) -> list[str]:
	missing: list[str] = []
	if not state.get(State.USER_QUERY):
		missing.append(State.USER_QUERY)
	return missing


def _todos_complete(todo_list: Any) -> bool:  # noqa: ANN401
	if todo_list is None:
		return False
	todos = getattr(todo_list, "todos", None)
	if todos is None and isinstance(todo_list, Iterable):
		todos = list(todo_list)
	if not todos:
		return False
	return all(getattr(todo, "state", None) == "done" for todo in todos)


def _validate_model(model: type[BaseModel], payload: Any) -> BaseModel:  # noqa: ANN401
	if isinstance(payload, model):
		return payload
	if hasattr(model, "model_validate"):
		return model.model_validate(payload)
	if isinstance(payload, Mapping):
		return model(**payload)
	return model(payload)


def _skip_redundant_analyst_calls(
	tool: BaseTool,
	args: dict[str, Any],
	tool_context: ToolContext,
) -> dict[str, Any] | None:
	state = tool_context.state
	tool_name = getattr(tool, "name", "")
	if tool_name == "update_todo":
		index = args.get("index")
		if index is None:
			return None
		todo_list = state.get(State.TODO_LIST)
		if todo_list is None:
			return None
		todos = getattr(todo_list, "todos", None)
		if todos is None and isinstance(todo_list, Iterable):
			todos = list(todo_list)
		if not todos:
			return None
		if 0 <= index < len(todos) and getattr(todos[index], "state", None) == "done":
			return {"success": True, "todos": todos}
		return None

	if tool_name == "set_research_mode":
		modes = state.get(State.ANALYST_RESEARCH_MODE) or []
		if modes:
			return {"success": True, "modes": modes}
		return None
	if tool_name == "analyst_agent":
		call_count = int(state.get(State.ANALYST_CALL_COUNT) or 0)
		if call_count >= 1:
			existing = state.get(State.ANALYST_FINDINGS)
			if existing:
				if isinstance(existing, dict):
					payload = dict(existing)
					payload.setdefault("assumptions", [])
					payload.setdefault("missing_data", [])
					return payload
				return {
					"findings": [{"detail": str(existing), "sources": []}],
					"assumptions": [],
					"missing_data": [],
				}
			return {"findings": [], "assumptions": [], "missing_data": []}
		state[State.ANALYST_CALL_COUNT] = call_count + 1
		if not state.get(State.ANALYST_FINDINGS):
			return None
		existing = state.get(State.ANALYST_FINDINGS)
		if isinstance(existing, dict):
			payload = dict(existing)
			payload.setdefault("assumptions", [])
			payload.setdefault("missing_data", [])
			return payload
		if isinstance(existing, str):
			return {
				"findings": [{"detail": existing, "sources": []}],
				"assumptions": [],
				"missing_data": [],
			}
		return {"findings": [{"detail": str(existing), "sources": []}], "assumptions": [], "missing_data": []}

	return None




def before_agent_callback(callback_context: CallbackContext) -> types.Content | None:
	"""Validate that required input state is present before agent execution."""
	return None


def after_agent_callback(callback_context: CallbackContext) -> None:
	"""Validate TODO completion and response format after agent execution."""
	state = callback_context.state
	todo_list = state.get(State.TODO_LIST)
	if todo_list is not None and not _todos_complete(todo_list):
		return

	recommendation = state.get(State.ADVISOR_RECOMMENDATION)
	if isinstance(recommendation, str):
		try:
			recommendation = json.loads(recommendation)
			state[State.ADVISOR_RECOMMENDATION] = recommendation
		except json.JSONDecodeError:
			pass
	try:
		_validate_model(AdvisorRecommendation, recommendation)
	except ValidationError as exc:
		msg = f"Advisor recommendation validation failed: {exc}"
		raise ValueError(msg) from exc


def create_advisor_agent(
	name: str,
	instruction: str,
	*,
	tools: Sequence[Any] | None = None,  # noqa: ANN401
	**kwargs: Any,
):
	"""Create the advisor agent with input/output validation callbacks."""
	return create_jpmc_agent(
		name=name,
		instruction=instruction,
		tools=tools,
		before_agent_callback=before_agent_callback,
		after_agent_callback=after_agent_callback,
		before_tool_callback=_skip_redundant_analyst_calls,
		output_key=State.ADVISOR_RECOMMENDATION,
		**kwargs,
	)


def create_advisor_root_agent():
	"""Create a full advisor agent with tool wiring for ADK discovery."""
	tools = [
		AgentTool(create_analyst_agent()),
		AgentTool(generate_profile()),
		AgentTool(respond_to_recommendation()),
		*TodoTool().get_tools(),
		*ResearchModeTool().get_tools(),
	]

	return create_advisor_agent(
		name="advisor_agent",
		instruction=get_advisor_agent_prompt,
		description="Orchestrates research and delivers client-ready investment guidance.",
		tools=tools,
	)


root_agent = create_advisor_root_agent()

app = App(
	name="advisor_agent",
	root_agent=root_agent,
	plugins=[TokenTracingPlugin(), StateSerializationPlugin()],
)
