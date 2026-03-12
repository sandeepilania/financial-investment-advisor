"""Prompt template for the client profile generator agent."""

from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.utils import instructions_utils

from core.state import State


PREAMBLE = """
You are a client simulator that generates a realistic investment profile.
""".strip()

PLANNING_MESSAGE = f"""
Create a plausible client profile that matches the user's query. Use realistic defaults
when details are missing. Do not ask questions. Return a JSON object that matches the
ClientProfile schema.

Required fields: name, age, risk_tolerance, investment_goals, current_investments (optional).

Here is the user query:
<user_query>
{{{State.USER_QUERY}}}
</user_query>
""".strip()


async def get_client_agent_prompt(ctx: ReadonlyContext) -> str:
	"""Generate the prompt for the client profile generator agent."""
	prompt = PREAMBLE + " " + PLANNING_MESSAGE
	return await instructions_utils.inject_session_state(prompt, ctx)
