"""LLM factory for Google ADK + LiteLLM."""

from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from core.config_manager import LLM_CONFIG


DEFAULT_API_BASES = {
    "github": "https://models.inference.ai.azure.com",
}


def _resolve_model_name(provider: str, model_name: str) -> str:
    """
    Resolve provider/model into the LiteLLM model string.

    GitHub Models uses an OpenAI-compatible endpoint, so we map:
        github + gpt-4o-mini  -> openai/gpt-4o-mini
    """
    provider = provider.lower()

    if provider == "github":
        return f"openai/{model_name}"

    return f"{provider}/{model_name}"


def _resolve_api_base(provider: str, api_base: str | None) -> str | None:
    """Use explicit api_base if provided, else provider defaults."""
    if api_base:
        return api_base
    return DEFAULT_API_BASES.get(provider.lower())


def _build_litellm_model() -> LiteLlm:
    """Build a LiteLlm model instance entirely from .env settings."""
    provider = LLM_CONFIG.get("LLM_PROVIDER", "openai").lower()
    model_name = LLM_CONFIG.get("LLM_MODEL_NAME", "gpt-4o-mini")
    api_key = LLM_CONFIG.get_api_key()
    api_base = _resolve_api_base(provider, LLM_CONFIG.get("LLM_API_BASE"))

    temperature = LLM_CONFIG.get_float("LLM_TEMPERATURE", 0.2)
    max_tokens = LLM_CONFIG.get_int("LLM_MAX_TOKENS", 1024)
    timeout = LLM_CONFIG.get_int("LLM_TIMEOUT", 60)
    num_retries = LLM_CONFIG.get_int("LLM_NUM_RETRIES", 3)

    if not api_key:
        raise ValueError(
            "LLM_API_KEY, GITHUB_API_KEY, or GITHUB_TOKEN is not set in the .env file."
        )

    model = _resolve_model_name(provider, model_name)

    kwargs = {
        "api_key": api_key,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "timeout": timeout,
        "num_retries": num_retries,
    }

    if api_base:
        kwargs["api_base"] = api_base

    return LiteLlm(
        model=model,
        **kwargs,
    )


def create_llm_agent(
    name: str,
    instruction: str,
    tools: list | None = None,
    **kwargs,
) -> LlmAgent:
    """Create an ADK LlmAgent backed by LiteLLM."""
    return LlmAgent(
        name=name,
        model=_build_litellm_model(),
        instruction=instruction,
        tools=tools or [],
        **kwargs,
    )