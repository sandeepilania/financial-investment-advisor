"""Demonstrate an explicit advisor-client resolution loop."""

from __future__ import annotations

import asyncio
import uuid

from google.genai import types
from google.adk.events import Event, EventActions
from google.adk.runners import Runner

from agents.client_agent.agent import respond_to_recommendation
from agents.fia_workflow import create_fia_workflow_runner
from core.loggers import log_tool_event
from core.state import State


async def _run_agent(runner: Runner, *, user_id: str, session_id: str, content: types.Content) -> None:
	async for event in runner.run_async(
		user_id=user_id,
		session_id=session_id,
		new_message=content,
	):
		log_tool_event(event)


async def _apply_state_delta(runner: Runner, *, user_id: str, session_id: str, delta: dict) -> None:
	session = await runner.session_service.get_session(
		app_name=runner.app.name,
		user_id=user_id,
		session_id=session_id,
	)
	event = Event(
		invocation_id=str(uuid.uuid4()),
		author="system",
		actions=EventActions(state_delta=delta),
	)
	await runner.session_service.append_event(session=session, event=event)


async def main() -> None:
	advisor_runner = create_fia_workflow_runner()
	client_runner = Runner(
		app_name=advisor_runner.app.name,
		agent=respond_to_recommendation(),
		session_service=advisor_runner.session_service,
	)

	user_id = "example_user"
	session_id = str(uuid.uuid4())
	base_query = "I want a strategy for investing in private pre-IPO secondaries with a moderate-risk profile."

	await advisor_runner.session_service.create_session(
		app_name=advisor_runner.app.name,
		user_id=user_id,
		session_id=session_id,
		state={State.USER_QUERY: base_query},
	)

	max_rounds = 2
	force_follow_up_round_1 = True
	for round_idx in range(1, max_rounds + 1):
		print(f"\n--- Advisor round {round_idx} ---")
		advisor_content = types.Content(role="user", parts=[types.Part(text=base_query)])
		print("Advisor run: start")
		await _run_agent(advisor_runner, user_id=user_id, session_id=session_id, content=advisor_content)
		print("Advisor run: end")

		print(f"\n--- Client eval {round_idx} ---")
		client_content = types.Content(role="user", parts=[types.Part(text="Evaluate the recommendation.")])
		await _run_agent(client_runner, user_id=user_id, session_id=session_id, content=client_content)

		session = await advisor_runner.session_service.get_session(
			app_name=advisor_runner.app.name,
			user_id=user_id,
			session_id=session_id,
		)
		client_response = session.state.get(State.CLIENT_RESPONSE) or {}
		resolved = bool(client_response.get("resolved"))
		follow_up = client_response.get("follow_up")

		if force_follow_up_round_1 and round_idx == 1:
			client_response = {
				"resolved": False,
				"follow_up": "I need a clearer allocation range and liquidity guidance for moderate-risk secondaries.",
			}
			await _apply_state_delta(
				advisor_runner,
				user_id=user_id,
				session_id=session_id,
				delta={State.CLIENT_RESPONSE: client_response},
			)
			resolved = False
			follow_up = client_response["follow_up"]

		print("Client response:", client_response)

		if resolved:
			break

		if follow_up:
			print("Follow-up requested. Rerunning advisor with client concern.")
			updated_query = f"{base_query}\nClient concern: {follow_up}"
			await _apply_state_delta(
				advisor_runner,
				user_id=user_id,
				session_id=session_id,
				delta={
					State.USER_QUERY: updated_query,
					State.ANALYST_FINDINGS: None,
					State.ANALYST_RESEARCH_MODE: None,
					State.ANALYST_CALL_COUNT: 0,
					State.ADVISOR_RECOMMENDATION: None,
					State.TODO_LIST: None,
				},
			)
			base_query = updated_query


if __name__ == "__main__":
	asyncio.run(main())
