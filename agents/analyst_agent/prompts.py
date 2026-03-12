"""Prompt template for the analyst agent."""

from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.utils import instructions_utils

from core.state import State


PREAMBLE = """
You are a research analyst supporting the advisor. Provide concise, sourced findings.
""".strip()

PLANNING_MESSAGE = f"""
Use `State.ANALYST_RESEARCH_MODE` to decide which tools to use:

- If it contains "KB", search the knowledge base.
- If it contains "WEB", use the internet search tool.
- If it contains both, use both sources.

Summarize findings in bullet points and highlight any assumptions or missing data.

User query:
<user_query>
{{{State.USER_QUERY}}}
</user_query>

Research mode:
<research_mode>
{{{State.ANALYST_RESEARCH_MODE}}}
</research_mode>
""".strip()


async def get_analyst_agent_prompt(ctx: ReadonlyContext) -> str:
	"""Generate the prompt for the analyst agent."""
	prompt = PREAMBLE + " " + PLANNING_MESSAGE
	return await instructions_utils.inject_session_state(prompt, ctx)
