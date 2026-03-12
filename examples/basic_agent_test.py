"""Basic ADK agent + InMemoryRunner smoke test.

Verifies end-to-end that:
  - _build_litellm_model() builds a LiteLlm pointed at GitHub Models
  - create_llm_agent() wraps it in an ADK LlmAgent
  - InMemoryRunner can create a session and run the agent
  - The agent produces at least one final response event

Run from the project root:
    python examples/basic_agent_test.py
"""

from __future__ import annotations

import asyncio
import uuid

from google.adk.runners import InMemoryRunner
from google.genai import types

from core.llm_factory import create_llm_agent
from core.loggers import WorkflowLogger


# Build the agent
agent = create_llm_agent(
    name="basic_test_agent",
    instruction=(
        "You are a concise financial assistant. "
        "Answer the user's question in two sentences or fewer."
    ),
)

# Runner
runner = InMemoryRunner(agent=agent, app_name="basic_agent_test")


async def chat(user_message: str, *, user_id: str, session_id: str) -> str:
    """Send one message and return the final text response."""
    content = types.Content(
        role="user",
        parts=[types.Part(text=user_message)],
    )

    final_text = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=content,
    ):
        # is_final_response() marks the last model turn
        if event.is_final_response() and event.content and event.content.parts:
            final_text = "".join(
                part.text for part in event.content.parts if part.text
            )

    return final_text


async def main() -> None:
    user_id = "test_user"
    session_id = str(uuid.uuid4())

    # Create the session explicitly before the first turn
    await runner.session_service.create_session(
        app_name=runner.app_name,
        user_id=user_id,
        session_id=session_id,
    )

    WorkflowLogger.log_stage_start(
        "basic_agent_test",
        {"message": "Starting agent conversation"},
    )

    questions = [
        "What is dollar-cost averaging?",
        "Should I invest in bonds when interest rates are rising?",
    ]

    for question in questions:
        WorkflowLogger.log_info("basic_agent_test", f"USER: {question}")
        answer = await chat(question, user_id=user_id, session_id=session_id)
        WorkflowLogger.log_info("basic_agent_test", f"AGENT: {answer}")

    WorkflowLogger.log_stage_complete(
        "basic_agent_test",
        {"message": "Conversation finished"},
    )


if __name__ == "__main__":
    asyncio.run(main())

