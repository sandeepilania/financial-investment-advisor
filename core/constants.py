"""Centralized, environment-aware constants for the project."""

from __future__ import annotations

from pathlib import Path

from core.config_manager import LLM_CONFIG


_ROOT_DIR = Path(__file__).resolve().parent.parent

_DEFAULT_KB_DATA_DIR = _ROOT_DIR / "knowledge_store" / "data"
_DEFAULT_KB_DB_DIR = _ROOT_DIR / "knowledge_store" / "lancedb"
_DEFAULT_KB_TABLE_NAME = "financial_kb"
_DEFAULT_KB_CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
_DEFAULT_KB_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

KB_DATA_DIR = Path(LLM_CONFIG.get("KNOWLEDGE_DATA_DIR", str(_DEFAULT_KB_DATA_DIR)))
KB_DB_DIR = LLM_CONFIG.get("KNOWLEDGE_DB_DIR", str(_DEFAULT_KB_DB_DIR))
KB_TABLE_NAME = LLM_CONFIG.get("KNOWLEDGE_TABLE_NAME", _DEFAULT_KB_TABLE_NAME)
KB_CROSS_ENCODER_MODEL = LLM_CONFIG.get(
    "KNOWLEDGE_CROSS_ENCODER_MODEL",
    _DEFAULT_KB_CROSS_ENCODER_MODEL,
)
KB_EMBEDDING_MODEL = LLM_CONFIG.get(
    "KNOWLEDGE_EMBEDDING_MODEL",
    _DEFAULT_KB_EMBEDDING_MODEL,
)

__all__ = [
    "KB_DATA_DIR",
    "KB_DB_DIR",
    "KB_TABLE_NAME",
    "KB_CROSS_ENCODER_MODEL",
    "KB_EMBEDDING_MODEL",
]
