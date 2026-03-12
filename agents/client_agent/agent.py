"""Client agent for generating a simulated client profile."""

from __future__ import annotations

from google.adk.agents.callback_context import CallbackContext
from google.genai import types
from pydantic import BaseModel

from core.jpmc_agent import create_jpmc_agent
from core.state import State
from schemas.client_profile import ClientProfile
from schemas.client_response import ClientResponse
from agents.client_agent.prompts import get_client_agent_prompt, get_client_response_prompt


MAX_CLIENT_REVIEW_ROUNDS = 2


def _client_response_guard(callback_context: CallbackContext) -> types.Content | None:
	state = callback_context.state
	review_count = int(state.get(State.CLIENT_REVIEW_COUNT) or 0)
	if review_count >= MAX_CLIENT_REVIEW_ROUNDS:
		state[State.CLIENT_RESPONSE] = {"resolved": True, "follow_up": None}
		return types.Content(
			role="assistant",
			parts=[types.Part(text='{"resolved": true, "follow_up": null}')],
		)
	if not state.get(State.ADVISOR_RECOMMENDATION):
		state[State.CLIENT_REVIEW_COUNT] = MAX_CLIENT_REVIEW_ROUNDS
		state[State.CLIENT_RESPONSE] = {"resolved": True, "follow_up": None}
		return types.Content(
			role="assistant",
			parts=[types.Part(text='{"resolved": true, "follow_up": null}')],
		)
	return None


def _increment_client_review_count(callback_context: CallbackContext) -> None:
	state = callback_context.state
	state[State.CLIENT_REVIEW_COUNT] = int(state.get(State.CLIENT_REVIEW_COUNT) or 0) + 1


def _extract_client_response(callback_context: CallbackContext) -> dict:
	response = getattr(callback_context, "response", None)
	output = getattr(callback_context, "output", None)
	content = response or output

	if isinstance(content, BaseModel):
		return content.model_dump()
	if isinstance(content, dict):
		return content

	text = None
	if isinstance(content, str):
		text = content
	else:
		parts = getattr(content, "parts", None) if content else None
		if parts:
			texts = [getattr(part, "text", "") for part in parts if getattr(part, "text", None)]
			text = "\n".join(texts) if texts else None

	if text:
		return {"resolved": False, "follow_up": text}
	return {}


def _apply_follow_up_reset(callback_context: CallbackContext) -> None:
	state = callback_context.state
	client_response = state.get(State.CLIENT_RESPONSE)
	if not client_response:
		client_response = _extract_client_response(callback_context)
		if client_response:
			state[State.CLIENT_RESPONSE] = client_response

	if not isinstance(client_response, dict):
		return

	resolved = bool(client_response.get("resolved"))
	follow_up = client_response.get("follow_up")
	review_count = int(state.get(State.CLIENT_REVIEW_COUNT) or 0)
	if resolved or not follow_up or review_count >= MAX_CLIENT_REVIEW_ROUNDS:
		return

	chat_history = state.get(State.CHAT_HISTORY) or []
	chat_history.append(
		{
			"turn": review_count,
			"user_query": state.get(State.USER_QUERY),
			"advisor_recommendation": state.get(State.ADVISOR_RECOMMENDATION),
			"client_response": client_response,
		}
	)
	state[State.CHAT_HISTORY] = chat_history

	updated_query = f"{state.get(State.USER_QUERY)}\nClient concern: {follow_up}"
	state[State.USER_QUERY] = updated_query
	state[State.ANALYST_FINDINGS] = None
	state[State.ANALYST_RESEARCH_MODE] = None
	state[State.ANALYST_CALL_COUNT] = 0
	state[State.ADVISOR_RECOMMENDATION] = None
	state[State.TODO_LIST] = None


def generate_profile(*, name: str = "client_agent"):
	"""Generate or refresh the simulated client profile."""
	return create_jpmc_agent(
		name=name,
		description="Generates a simulated client profile based on the user query.",
		instruction=get_client_agent_prompt,
		output_key=State.CLIENT_PROFILE,
		output_schema=ClientProfile,
	)


def respond_to_recommendation(*, name: str = "client_response_agent"):
	"""Evaluate whether the advisor recommendation resolves the conversation."""
	return create_jpmc_agent(
		name=name,
		description="Evaluates the advisor recommendation from the client's perspective.",
		instruction=get_client_response_prompt,
		output_key=State.CLIENT_RESPONSE,
		output_schema=ClientResponse,
		before_agent_callback=_client_response_guard,
		after_agent_callback=[_increment_client_review_count, _apply_follow_up_reset],
	)


def is_resolved(response: ClientResponse | dict | None) -> bool:
	"""Return True when the client considers the recommendation resolved."""
	if response is None:
		return False
	if isinstance(response, ClientResponse):
		return response.resolved
	return bool(response.get("resolved"))


def create_client_agent(*, name: str = "client_agent"):
	"""Backward-compatible alias for profile generation."""
	return generate_profile(name=name)
