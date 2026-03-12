"""End-to-end example that exercises client, analyst, and advisor flows."""

from __future__ import annotations

import asyncio
import uuid

from google.genai import types

from agents.fia_workflow import create_fia_workflow_runner
from core.loggers import log_tool_event
from core.state import State


async def main() -> None:
    runner = create_fia_workflow_runner()
    print("Starting end-to-end workflow example...")

    user_id = "example_user"
    session_id = str(uuid.uuid4())

    query_example1 = "I want a strategy for investing in private pre‑IPO secondaries with a moderate‑risk profile"
    # query_example2 = (
    #         "I am planning for a moderate-risk retirement goal. Please explain the "
    #         "long-term strategy using core concepts like diversification and bond laddering, "
    #         "and also incorporate the latest 2026 interest rate and inflation outlook."
    #     )
    initial_state = {
        State.USER_QUERY: query_example1
    }

    await runner.session_service.create_session(
        app_name=runner.app.name,
        user_id=user_id,
        session_id=session_id,
        state=initial_state,
    )

    content = types.Content(
        role="user",
        parts=[types.Part(text=initial_state[State.USER_QUERY])],
    )

    async def _run_once() -> None:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content,
        ):
            log_tool_event(event)
            if event.is_final_response():
                print("Final response event received.")

    await _run_once()

    session = await runner.session_service.get_session(
        app_name=runner.app.name,
        user_id=user_id,
        session_id=session_id,
    )

    client_profile = session.state.get(State.CLIENT_PROFILE)
    client_response = session.state.get(State.CLIENT_RESPONSE)
    recommendation = session.state.get(State.ADVISOR_RECOMMENDATION)

    print("Client profile:\n", client_profile)
    print("Client response:\n", client_response)
    print("Final recommendation:\n", recommendation)


if __name__ == "__main__":
    asyncio.run(main())
