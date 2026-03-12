"""Advisor agent construction and validation callbacks."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
import json
from typing import Any

from google.adk.agents.base_agent import AfterAgentCallback, BeforeAgentCallback
from google.adk.agents.callback_context import CallbackContext
from google.genai import types
from pydantic import BaseModel, ValidationError

from core.jpmc_agent import create_jpmc_agent
from core.state import State
from schemas.advisor_recommendation import AdvisorRecommendation

def _missing_required_state(state: Mapping[str, Any]) -> list[str]:
	missing: list[str] = []
	if not state.get(State.USER_QUERY):
		missing.append(State.USER_QUERY)
	if not state.get(State.CLIENT_PROFILE):
		missing.append(State.CLIENT_PROFILE)
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




def before_agent_callback(callback_context: CallbackContext) -> types.Content | None:
	"""Validate that required input state is present before agent execution."""
	if _missing_required_state(callback_context.state):
		return types.Content(
			role="assistant",
			parts=[types.Part(text="Missing user query or client profile. Skipping advisor agent.")],
		)
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
		output_key=State.ADVISOR_RECOMMENDATION,
		**kwargs,
	)
