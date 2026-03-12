"""Client agent for generating a simulated client profile."""

from __future__ import annotations

from google.adk.agents.callback_context import CallbackContext
from google.genai import types

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
		after_agent_callback=_increment_client_review_count,
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
