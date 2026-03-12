"""End-to-end example for the advisor-led workflow."""

from __future__ import annotations

import asyncio
import uuid

from google.genai import types

from agents.fia_workflow import create_fia_workflow_runner
from core.state import State


async def main() -> None:
    runner = create_fia_workflow_runner()
    print("Starting advisor workflow example...")

    user_id = "example_user"
    session_id = str(uuid.uuid4())

    initial_state = {
        State.USER_QUERY: "What investment strategy would you recommend for a moderate-risk retirement goal, considering current interest rates, inflation, and market conditions in 2026?",
        State.CLIENT_PROFILE: {
            "name": "Alex",
            "age": 35,
            "risk_tolerance": "moderate",
            "investment_goals": ["retirement"],
            "current_investments": ["index funds"],
        },
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
            print("Event type:", event)
            if event.content and event.content.parts:
                text = "".join(part.text for part in event.content.parts if part.text)
                if text:
                    print("Event:", text)
            if event.is_final_response():
                print("Final response event received.")

    await _run_once()

    session = await runner.session_service.get_session(
        app_name=runner.app.name,
        user_id=user_id,
        session_id=session_id,
    )

    recommendation = session.state.get(State.ADVISOR_RECOMMENDATION)
    print("Final recommendation:\n", recommendation)


if __name__ == "__main__":
    asyncio.run(main())
