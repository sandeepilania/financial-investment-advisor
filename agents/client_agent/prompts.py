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

RECOMMENDATION_RESPONSE_MESSAGE = f"""
Review the advisor recommendation from the client's perspective. Decide if it resolves
the user's question or if a follow-up concern is still needed. Return a JSON object that
matches the ClientResponse schema.

If the recommendation is sufficient, set resolved to true and follow_up to null.
If more is needed, set resolved to false and provide a concise follow-up concern.
Always ask a follow-up question when assumptions or missing_data are present in either
the analyst findings or the advisor recommendation.
Also ask a follow-up if inline citations are missing in the advisor summary or recommendation.

Here is the user query:
<user_query>
{{{State.USER_QUERY}}}
</user_query>

Here is the client profile:
<client_profile>
{{{State.CLIENT_PROFILE}}}
</client_profile>

Here is the advisor recommendation:
<advisor_recommendation>
{{{State.ADVISOR_RECOMMENDATION}}}
</advisor_recommendation>

Here are the analyst findings (if any):
<analyst_findings>
{{{State.ANALYST_FINDINGS}}}
</analyst_findings>
""".strip()


async def get_client_agent_prompt(ctx: ReadonlyContext) -> str:
	"""Generate the prompt for the client profile generator agent."""
	state = ctx.state
	user_query = state.get(State.USER_QUERY, "")

	prompt = PREAMBLE + " " + PLANNING_MESSAGE
	prompt = prompt.replace(f"{{{{{State.USER_QUERY}}}}}", str(user_query))
	return prompt


async def get_client_response_prompt(ctx: ReadonlyContext) -> str:
	"""Generate the prompt for the client recommendation response agent."""
	state = ctx.state
	user_query = state.get(State.USER_QUERY, "")
	client_profile = state.get(State.CLIENT_PROFILE, "")
	advisor_recommendation = state.get(State.ADVISOR_RECOMMENDATION, "")
	analyst_findings = state.get(State.ANALYST_FINDINGS, "")

	prompt = PREAMBLE + " " + RECOMMENDATION_RESPONSE_MESSAGE
	prompt = prompt.replace(f"{{{{{State.USER_QUERY}}}}}", str(user_query))
	prompt = prompt.replace(f"{{{{{State.CLIENT_PROFILE}}}}}", str(client_profile))
	prompt = prompt.replace(f"{{{{{State.ADVISOR_RECOMMENDATION}}}}}", str(advisor_recommendation))
	prompt = prompt.replace(f"{{{{{State.ANALYST_FINDINGS}}}}}", str(analyst_findings))
	return prompt
