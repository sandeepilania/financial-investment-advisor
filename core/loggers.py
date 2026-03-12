"""Common logging utilities for the financial investment advisor.

Provides structured, stage-based logging across all agents and services.
"""

import functools
import json
import os
import sys
from typing import Any, Literal

from loguru import logger
from pydantic import BaseModel


def strip_none(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively remove None values from a dict.

    Only strips None — preserves 0, False, and empty strings
    since those can be meaningful log values.
    """
    return {k: strip_none(v) if isinstance(v, dict) else v for k, v in data.items() if v is not None}


USE_LNAV_LOG_FORMAT = os.getenv("USE_LNAV_LOG_FORMAT")
USE_LNAV_FORMAT = os.getenv("USE_LNAV_FORMAT")
_USE_JSON_LOGS = bool(USE_LNAV_LOG_FORMAT or USE_LNAV_FORMAT)


class LogObject(BaseModel):
    """Structured log object for workflow logging."""

    stage: str
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"]
    message: str
    data: dict[str, Any] | BaseModel | None = None
    strip_none_values: bool = False

    def to_json(self) -> str:
        data = self.data
        if self.strip_none_values and isinstance(data, dict):
            data = strip_none(data)

        payload = {
            "stage": self.stage,
            "level": self.level,
            "message": self.message,
            "data": data,
        }

        return json.dumps(payload, ensure_ascii=True)

    def __str__(self) -> str:
        if _USE_JSON_LOGS:
            return self.to_json()

        data = self.data
        if self.strip_none_values and isinstance(data, dict):
            data = strip_none(data)

        if isinstance(data, BaseModel):
            pretty_data = data.model_dump_json(indent=2)
        else:
            pretty_data = json.dumps(data, indent=2) if data is not None else None

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
    def log_stage_start(stage: str, data: dict[str, Any] | None = None, *, strip_none: bool = False) -> None:
        """Log the start of a stage at INFO level.

        Args:
            stage: Stage name (e.g. "ADVISOR_CALL", "SEARCH")
            data: Optional context data
            strip_none: Remove None values from data before logging
        """
        logger.opt(depth=1).info(
            LogObject(stage=stage, level="INFO", message="START", data=data, strip_none_values=strip_none)
        )

    @staticmethod
    def log_stage_progress(stage: str, message: str, data: dict[str, Any] | None = None, *, strip_none: bool = False) -> None:
        """Log mid-stage progress at DEBUG level.

        Args:
            stage: Stage name
            message: Description of current activity
            data: Optional progress data
            strip_none: Remove None values from data before logging
        """
        logger.opt(depth=1).debug(
            LogObject(stage=stage, level="DEBUG", message=message, data=data, strip_none_values=strip_none)
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
                strip_none_values=True,
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
    def log_warning(stage: str, message: str, data: dict[str, Any] | None = None, *, strip_none: bool = False) -> None:
        """Log a warning at WARNING level.

        Args:
            stage: Stage name
            message: Warning message
            data: Optional additional data
            strip_none: Remove None values from data before logging
        """
        logger.opt(depth=1).warning(
            LogObject(stage=stage, level="WARNING", message=message, data=data, strip_none_values=strip_none)
        )

    @staticmethod
    def log_info(stage: str, message: str, data: dict[str, Any] | None = None, *, strip_none: bool = False) -> None:
        """Log an informational message at INFO level.

        Args:
            stage: Stage name
            message: Info message
            data: Optional additional data
            strip_none: Remove None values from data before logging
        """
        logger.opt(depth=1).info(
            LogObject(stage=stage, level="INFO", message=message, data=data, strip_none_values=strip_none)
        )


def _truncate_value(value: Any, max_len: int = 300) -> Any:
    if isinstance(value, str):
        return value if len(value) <= max_len else value[:max_len] + "..."
    return value


def _summarize_result(result: Any) -> dict[str, Any] | None:
    if result is None:
        return None
    if isinstance(result, list):
        return {"items": len(result)}
    if isinstance(result, dict):
        return {"keys": list(result.keys())[:10], "key_count": len(result)}
    return {"type": type(result).__name__}


def _clean_call_args(args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any]:
    cleaned_args = []
    for arg in args:
        if arg.__class__.__name__ == "ToolContext":
            continue
        cleaned_args.append(_truncate_value(arg))

    cleaned_kwargs = {
        key: _truncate_value(value)
        for key, value in kwargs.items()
        if key != "tool_context"
    }

    return {"args": cleaned_args, "kwargs": cleaned_kwargs}


def log_tool_call(stage: str):
    """Decorator that logs tool invocation start/complete/error via WorkflowLogger."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any):
            WorkflowLogger.log_stage_start(stage, data=_clean_call_args(args, kwargs), strip_none=True)
            try:
                result = func(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001
                WorkflowLogger.log_error(stage, "FAILED", exc)
                raise
            WorkflowLogger.log_stage_complete(stage, summary=_summarize_result(result))
            return result

        return wrapper

    return decorator


def log_tool_event(event: Any) -> None:  # noqa: ANN401
    """Log ADK tool call/response events with a structured summary."""
    content = getattr(event, "content", None)
    parts = getattr(content, "parts", None) if content else None
    if not parts:
        return

    for part in parts:
        function_call = getattr(part, "function_call", None)
        if function_call:
            WorkflowLogger.log_stage_progress(
                "TOOL_CALL",
                function_call.name,
                data={
                    "args": _truncate_value(getattr(function_call, "args", None)),
                    "id": getattr(function_call, "id", None),
                },
                strip_none=True,
            )

        function_response = getattr(part, "function_response", None)
        if function_response:
            WorkflowLogger.log_stage_progress(
                "TOOL_RESPONSE",
                function_response.name,
                data={
                    "response": _truncate_value(getattr(function_response, "response", None)),
                    "id": getattr(function_response, "id", None),
                },
                strip_none=True,
            )
