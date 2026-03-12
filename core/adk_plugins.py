"""ADK plugins used by the workflow runner."""

from __future__ import annotations

from time import perf_counter

from google.adk.plugins.base_plugin import BasePlugin
from pydantic import BaseModel

from core.loggers import WorkflowLogger


class TokenTracingPlugin(BasePlugin):
	"""Collect basic token usage and latency for each model call."""

	def __init__(self) -> None:
		super().__init__(name="token_tracing")

	async def before_model_callback(self, *, callback_context, llm_request):
		callback_context.state["model_start_ts"] = perf_counter()

	async def after_model_callback(self, *, callback_context, llm_response):
		start = callback_context.state.get("model_start_ts")
		latency_ms = (perf_counter() - start) * 1000 if start else None

		usage = getattr(llm_response, "usage", None) or getattr(
			llm_response, "token_usage", None
		)
		usage_metadata = getattr(llm_response, "usage_metadata", None) or getattr(
			llm_response, "usageMetadata", None
		)
		if usage_metadata is None and isinstance(llm_response, BaseModel):
			payload = llm_response.model_dump()
			usage_metadata = payload.get("usageMetadata") or payload.get("usage_metadata")

		log_payload = {
			"agent": callback_context.agent_name,
			"latency_ms": latency_ms,
			"usage": usage,
			"usage_metadata": usage_metadata,
		}
		WorkflowLogger.log_info("TOKEN_TRACING", "MODEL_COMPLETE", data=log_payload, prune_falsy=True)

	async def on_model_error_callback(self, *, callback_context, llm_request, error):
		WorkflowLogger.log_error("TOKEN_TRACING", "MODEL_ERROR", error=error)
		return None


def _sanitize_value(value: object) -> object:
	if isinstance(value, BaseModel):
		return value.model_dump()
	if isinstance(value, dict):
		return {key: _sanitize_value(val) for key, val in value.items()}
	if isinstance(value, (list, tuple, set)):
		return [_sanitize_value(item) for item in value]
	return value


class StateSerializationPlugin(BasePlugin):
	"""Ensure event state deltas are JSON serializable."""

	def __init__(self) -> None:
		super().__init__(name="state_serialization")

	async def on_event_callback(self, *, invocation_context, event):
		state_delta = getattr(event.actions, "state_delta", None)
		if state_delta:
			event.actions.state_delta = _sanitize_value(state_delta)
		return None
