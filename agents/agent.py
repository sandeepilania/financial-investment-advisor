"""Root agent entrypoint for ADK Web UI discovery."""

from __future__ import annotations

from google.adk.apps.app import App
from google.adk.tools.agent_tool import AgentTool

from core.adk_plugins import StateSerializationPlugin, TokenTracingPlugin
from agents.analyst_agent.agent import create_analyst_agent
from agents.advisor_agent.agent import create_advisor_agent
from agents.advisor_agent.prompts import get_advisor_agent_prompt
from agents.client_agent.agent import generate_profile, respond_to_recommendation
from tools.research_mode_tool import ResearchModeTool
from tools.todo_tool import TodoTool


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
	name="advisor_agent",
	root_agent=root_agent,
	plugins=[TokenTracingPlugin(), StateSerializationPlugin()],
)
