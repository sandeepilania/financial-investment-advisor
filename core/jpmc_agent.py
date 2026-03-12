"""ADK LlmAgent wrapper using the shared LiteLLM configuration."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.agents.base_agent import AfterAgentCallback, BeforeAgentCallback
from google.adk.agents.llm_agent import (
    AfterModelCallback,
    AfterToolCallback,
    BeforeModelCallback,
    BeforeToolCallback,
    InstructionProvider,
)
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.base_toolset import BaseToolset
from google.genai import types

from core.llm_factory import _build_litellm_model


def create_jpmc_agent(
    name: str,
    instruction: str | InstructionProvider,
    *,
    description: str | None = None,
    tools: Sequence[BaseTool | BaseToolset] | None = None,
    before_agent_callback: BeforeAgentCallback | None = None,
    after_agent_callback: AfterAgentCallback | None = None,
    before_model_callback: BeforeModelCallback | Sequence[BeforeModelCallback] | None = None,
    after_model_callback: AfterModelCallback | Sequence[AfterModelCallback] | None = None,
    before_tool_callback: BeforeToolCallback | Sequence[BeforeToolCallback] | None = None,
    after_tool_callback: AfterToolCallback | Sequence[AfterToolCallback] | None = None,
    include_contents: str | None = None,
    generate_content_config: types.GenerateContentConfig | None = None,
    **kwargs: Any,
) -> LlmAgent:
    """Create an ADK LlmAgent with the shared LiteLLM configuration.

    This wrapper keeps the LiteLLM settings centralized while exposing the full
    ADK callback surface for agent construction.
    """
    agent_kwargs: dict[str, Any] = {
        "name": name,
        "description": description,
        "model": _build_litellm_model(),
        "instruction": instruction,
        "tools": list(tools) if tools is not None else [],
        "before_agent_callback": before_agent_callback,
        "after_agent_callback": after_agent_callback,
        "before_model_callback": before_model_callback,
        "after_model_callback": after_model_callback,
        "before_tool_callback": before_tool_callback,
        "after_tool_callback": after_tool_callback,
        "generate_content_config": generate_content_config,
        **kwargs,
    }

    if include_contents is not None:
        agent_kwargs["include_contents"] = include_contents

    return LlmAgent(
        **agent_kwargs,
    )
