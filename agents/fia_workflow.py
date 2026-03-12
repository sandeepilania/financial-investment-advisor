"""Advisor-led workflow runner for the Financial Investment Advisor app."""

from __future__ import annotations

from google.adk.apps.app import App
from google.adk.runners import Runner
from google.adk.sessions import BaseSessionService, InMemorySessionService
from google.adk.tools.agent_tool import AgentTool

from agents.analyst_agent.agent import create_analyst_agent
from agents.advisor_agent.agent import create_advisor_agent
from agents.advisor_agent.prompts import get_advisor_agent_prompt
from agents.client_agent.agent import generate_profile, respond_to_recommendation
from core.adk_plugins import TokenTracingPlugin
from tools.research_mode_tool import ResearchModeTool
from tools.todo_tool import TodoTool


APP_NAME = "financial_investment_advisor"


def create_fia_workflow_runner(
	session_service: BaseSessionService | None = None,
) -> Runner:
	"""Create the advisor-led workflow runner.

	The advisor agent is the root orchestrator. It can call tools (and other
	agents via AgentTool, if added) to complete the workflow.
	"""
	tools = [
		AgentTool(create_analyst_agent()),
		AgentTool(generate_profile()),
		AgentTool(respond_to_recommendation()),
		*TodoTool().get_tools(),
		*ResearchModeTool().get_tools(),
	]

	root_agent = create_advisor_agent(
		name="advisor_agent",
		instruction=get_advisor_agent_prompt,
		description="Orchestrates research and delivers client-ready investment guidance.",
		tools=tools,
	)

	app = App(
		name=APP_NAME,
		root_agent=root_agent,
		plugins=[TokenTracingPlugin()],
	)

	if not session_service:
		session_service = InMemorySessionService()

	return Runner(
		app=app,
		session_service=session_service,
	)
