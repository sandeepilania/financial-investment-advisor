"""Client agent for generating a simulated client profile."""

from __future__ import annotations

from core.jpmc_agent import create_jpmc_agent
from core.state import State
from schemas.client_profile import ClientProfile
from agents.client_agent.prompts import get_client_agent_prompt


def create_client_agent(*, name: str = "client_agent"):
	"""Create the client agent that generates a ClientProfile."""
	return create_jpmc_agent(
		name=name,
		description="Generates a simulated client profile based on the user query.",
		instruction=get_client_agent_prompt,
		output_key=State.CLIENT_PROFILE,
		output_schema=ClientProfile,
	)
