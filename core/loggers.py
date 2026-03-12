"""Common logging utilities for the financial investment advisor.

Provides structured, stage-based logging across all agents and services.
"""

import functools
import json
import os
import sys
from typing import Any, Literal

from typing_extensions import override

from loguru import logger
from pydantic import BaseModel


USE_LNAV_FORMAT = (os.environ.get("USE_LNAV_LOG_FORMAT") or os.environ.get("USE_LNAV_FORMAT")) in [
    "1",
    "true",
    "True",
    "y",
    "Y",
    "yes",
    "YES",
]


def prune_falsy_values(data: Any) -> Any:
    """Recursively remove falsy values from dicts/lists, preserving numeric zeros."""
    if isinstance(data, (int, float)):
        return data

    if isinstance(data, list):
        return [prune_falsy_values(item) for item in data]

    if isinstance(data, dict):
        return {k: prune_falsy_values(v) for k, v in data.items() if v}

    return data


def _json_default(value: Any) -> Any:  # noqa: ANN401
    """Fallback JSON encoder for log payloads."""
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, (set, tuple)):
        return list(value)
    return str(value)


def _scrub_embeddings(data: Any) -> Any:  # noqa: ANN401
    """Remove embedding/vector fields from nested log payloads."""
    if isinstance(data, list):
        return [_scrub_embeddings(item) for item in data]

    if isinstance(data, dict):
        scrubbed: dict[str, Any] = {}
        for key, value in data.items():
            if key in {"vector", "embedding", "embeddings"}:
                continue
            scrubbed[key] = _scrub_embeddings(value)
        return scrubbed

    return data


class LogObject(BaseModel):
    """Structured log object for workflow logging."""

    stage: str
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"]
    message: str
    data: dict[str, Any] | BaseModel | None = None
    prune_falsy: bool = False

    @override
    def model_dump_json(self, *args: object, **kwargs: object) -> str:
        obj_dict = self.model_dump(*args, **kwargs)

        if self.data is None:
            obj_dict.pop("data", None)

        try:
            return json.dumps(obj_dict, default=_json_default)
        except TypeError:
            _ = obj_dict.pop("data", None)
            return json.dumps(obj_dict, default=_json_default)

    def __str__(self) -> str:
        if self.prune_falsy and self.data is not None:
            self.data = prune_falsy_values(self.data)

        if USE_LNAV_FORMAT:
            return self.model_dump_json()

        data = self.data

        if isinstance(data, BaseModel):
            pretty_data = data.model_dump_json(indent=2)
        else:
            pretty_data = json.dumps(data, indent=2, default=_json_default) if data is not None else None

        return f"[{self.stage}] {self.level}: {self.message}" + (f"\nData: {pretty_data}" if pretty_data else "")

    def __repr__(self) -> str:
        return f"LogObject(stage={self.stage!r}, level={self.level!r}, message={self.message!r}, data={self.data!r})"


fmt = (
    "[<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green>] <level>{level: <5}</level> <cyan>{name}</cyan>:<cyan>"
    "{function}</cyan>:<cyan>{line}</cyan> <level>{message}</level>"
)
logger.remove()
_ = logger.add(sys.stderr, level="DEBUG", format=fmt)


class WorkflowLogger:
    """Structured, stage-based logging for agents and services.

    Usage:
        WorkflowLogger.log_info("ADVISOR", "Sending response to client")
    """

    @staticmethod
    def log_stage_start(stage: str, data: dict[str, Any] | None = None, *, prune_falsy: bool = False) -> None:
        """Log the start of a stage at INFO level.

        Args:
            stage: Stage name (e.g. "ADVISOR_CALL", "SEARCH")
            data: Optional context data
            strip_none: Remove None values from data before logging
        """
        logger.opt(depth=1).info(
            LogObject(stage=stage, level="INFO", message="START", data=data, prune_falsy=prune_falsy)
        )

    @staticmethod
    def log_stage_progress(
        stage: str, message: str, data: dict[str, Any] | None = None, *, prune_falsy: bool = False
    ) -> None:
        """Log mid-stage progress at DEBUG level.

        Args:
            stage: Stage name
            message: Description of current activity
            data: Optional progress data
            strip_none: Remove None values from data before logging
        """
        logger.opt(depth=1).debug(
            LogObject(stage=stage, level="DEBUG", message=message, data=data, prune_falsy=prune_falsy)
        )

    @staticmethod
    def log_stage_complete(stage: str, summary: dict[str, Any] | None = None, execution_time: float | None = None) -> None:
        """Log successful stage completion at INFO level.

        Args:
            stage: Stage name
            summary: Optional result summary
            execution_time: Optional duration in seconds
        """
        logger.opt(depth=1).info(
            LogObject(
                stage=stage,
                level="INFO",
                message="COMPLETE",
                data={"summary": summary, "execution_time": execution_time},
                prune_falsy=True,
            )
        )

    @staticmethod
    def log_error(stage: str, message: str, error: Exception | None = None) -> None:
        """Log an error with optional exception details.

        Args:
            stage: Stage where the error occurred
            message: What went wrong
            error: Optional exception for additional context
        """
        logger.opt(depth=1).error(
            LogObject(stage=stage, level="ERROR", message=message, data={"error": str(error)} if error else None)
        )

    @staticmethod
    def log_warning(stage: str, message: str, data: dict[str, Any] | None = None, *, prune_falsy: bool = False) -> None:
        """Log a warning at WARNING level.

        Args:
            stage: Stage name
            message: Warning message
            data: Optional additional data
            strip_none: Remove None values from data before logging
        """
        logger.opt(depth=1).warning(
            LogObject(stage=stage, level="WARNING", message=message, data=data, prune_falsy=prune_falsy)
        )

    @staticmethod
    def log_info(stage: str, message: str, data: dict[str, Any] | None = None, *, prune_falsy: bool = False) -> None:
        """Log an informational message at INFO level.

        Args:
            stage: Stage name
            message: Info message
            data: Optional additional data
            strip_none: Remove None values from data before logging
        """
        logger.opt(depth=1).info(
            LogObject(stage=stage, level="INFO", message=message, data=data, prune_falsy=prune_falsy)
        )


def _clean_call_args(args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any]:
    cleaned_args = []
    for arg in args:
        if arg.__class__.__name__ == "ToolContext":
            continue
        if arg.__class__.__name__.endswith("Tool"):
            continue
        cleaned_args.append(_scrub_embeddings(arg))

    cleaned_kwargs = {
        key: _scrub_embeddings(value)
        for key, value in kwargs.items()
        if key != "tool_context"
    }

    return {"args": cleaned_args, "kwargs": cleaned_kwargs}


def log_tool_call(stage: str):
    """Decorator that logs tool invocation start/complete/error via WorkflowLogger."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(
            *args: Any,
            __log_start=WorkflowLogger.log_stage_start,
            __log_complete=WorkflowLogger.log_stage_complete,
            __log_error=WorkflowLogger.log_error,
            __clean=_clean_call_args,
            **kwargs: Any,
        ):
            __log_start(stage, data=__clean(args, kwargs), prune_falsy=True)
            try:
                result = func(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001
                __log_error(stage, "FAILED", exc)
                raise
            __log_complete(stage, summary={"result": result})
            return result

        wrapper.__globals__.update(func.__globals__)
        wrapper.__annotations__ = func.__annotations__
        return wrapper

    return decorator


def log_tool_event(event: Any) -> None:  # noqa: ANN401
    """Log ADK tool call/response events with a structured summary."""
    content = getattr(event, "content", None)
    parts = getattr(content, "parts", None) if content else None
    if not parts:
        return

    tool_logger = logger.patch(lambda record: record.update(name="tool_events"))

    for part in parts:
        function_call = getattr(part, "function_call", None)
        if function_call:
            tool_logger.opt(depth=2).debug(
                LogObject(
                    stage="TOOL_CALL",
                    level="DEBUG",
                    message=function_call.name,
                    data={
                        "args": getattr(function_call, "args", None),
                        "id": getattr(function_call, "id", None),
                    },
                    prune_falsy=True,
                )
            )

        function_response = getattr(part, "function_response", None)
        if function_response:
            tool_logger.opt(depth=2).debug(
                LogObject(
                    stage="TOOL_RESPONSE",
                    level="DEBUG",
                    message=function_response.name,
                    data={
                        "response": getattr(function_response, "response", None),
                        "id": getattr(function_response, "id", None),
                    },
                    prune_falsy=True,
                )
            )
