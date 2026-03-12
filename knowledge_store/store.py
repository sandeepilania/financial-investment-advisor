"""KnowledgeStore — LanceDB-backed store with hybrid retrieval and cross-encoder reranking.

Ingestion
---------
    ks = KnowledgeStore()
    ks.ingest()

Retrieval
---------
    results = ks.search("best ETFs for retirement", top_k=5)
    results = ks.search(
        "bond allocation",
        top_k=5,
        filters="risk_profile = 'low'",
    )
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import lancedb

from core.constants import (
    KB_CROSS_ENCODER_MODEL,
    KB_DATA_DIR,
    KB_DB_DIR,
    KB_TABLE_NAME,
)
from core.loggers import WorkflowLogger
from knowledge_store.parser import load_all_rows
from schemas.kb_chunk import KBChunk

_STAGE = "KNOWLEDGE_STORE"

_DATA_DIR = KB_DATA_DIR
_DB_DIR = KB_DB_DIR
_TABLE_NAME = KB_TABLE_NAME
_CROSS_ENCODER_MODEL = KB_CROSS_ENCODER_MODEL


class KnowledgeStore:
    """LanceDB-backed knowledge store with hybrid retrieval and cross-encoder reranking."""

    def __init__(
        self,
        db_dir: str = _DB_DIR,
        table_name: str = _TABLE_NAME,
        data_dir: Path = _DATA_DIR,
        cross_encoder_model: str = _CROSS_ENCODER_MODEL,
    ) -> None:
        self._db_dir = db_dir
        self._table_name = table_name
        self._data_dir = data_dir
        self._cross_encoder_model_name = cross_encoder_model

        self._db = lancedb.connect(db_dir)
        self._table = None
        self._cross_encoder = self._load_cross_encoder()

        if table_name in self._db.table_names():
            self._table = self._db.open_table(table_name)
            WorkflowLogger.log_info(
                _STAGE,
                f"Opened existing table '{table_name}'",
                {"rows": self._table.count_rows()},
            )

    # Ingestion
 
    def ingest(self, overwrite: bool = False) -> None:
        """Parse all markdown docs and load them into LanceDB.

        Args:
            overwrite: Re-ingest even if the table already exists.
        """
        WorkflowLogger.log_stage_start(
            _STAGE,
            {"data_dir": str(self._data_dir), "overwrite": overwrite},
        )

        if self._table is not None and not overwrite:
            WorkflowLogger.log_warning(
                _STAGE,
                "Table already exists — skipping ingestion. Pass overwrite=True to re-ingest.",
            )
            return

        rows = load_all_rows(self._data_dir)
        WorkflowLogger.log_stage_progress(_STAGE, f"Parsed {len(rows)} chunks from markdown files")

        self._table = self._db.create_table(self._table_name, schema=KBChunk, mode="overwrite")
        self._table.add(rows)
        WorkflowLogger.log_stage_progress(_STAGE, f"Inserted {len(rows)} rows into '{self._table_name}'")

        self._create_indexes()
        WorkflowLogger.log_stage_complete(_STAGE, {"rows_ingested": len(rows)})

    def _create_indexes(self) -> None:
        """Create vector, FTS, and scalar indexes for efficient hybrid retrieval."""
        row_count = self._table.count_rows()
        # Keep vector search exact for the demo: no ANN index. Hybrid search still works.
        WorkflowLogger.log_stage_progress(
            _STAGE,
            "Skipped vector index (exact search via flat scan)",
            {"rows": row_count},
        )

        self._table.create_fts_index("text_for_embedding", replace=True)
        WorkflowLogger.log_stage_progress(
            _STAGE,
            "Created FTS index on 'text_for_embedding'",
        )

        scalar_indexes: list[tuple[str, str]] = [
            ("category", "BITMAP"),
            ("risk_profile", "BITMAP"),
            ("asset_class", "BITMAP"),
            ("source", "BITMAP"),
            ("tags", "LABEL_LIST"),
        ]
        for col, idx_type in scalar_indexes:
            self._table.create_scalar_index(col, index_type=idx_type)
        WorkflowLogger.log_stage_progress(
            _STAGE,
            "Created scalar indexes",
            {"columns": [c for c, _ in scalar_indexes]},
        )

    def _load_cross_encoder(self):
        WorkflowLogger.log_stage_progress(
            _STAGE,
            f"Loading cross-encoder '{self._cross_encoder_model_name}'",
        )
        from sentence_transformers import CrossEncoder  # noqa: PLC0415

        return CrossEncoder(self._cross_encoder_model_name)

    
    # Retrieval    

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        candidate_k: int = 20,
        filters: str | None = None,
        use_reranker: bool = True,
    ) -> list[dict[str, Any]]:
        """Hybrid vector + FTS search with optional cross-encoder reranking.

        Args:
            query:        Natural-language query string.
            top_k:        Number of results to return.
            candidate_k:  Candidates retrieved before reranking.
            filters:      SQL-style WHERE clause, e.g. ``"risk_profile = 'low'"``.
            use_reranker: Apply cross-encoder reranking on candidates.

        Returns:
            List of result dicts (all KBChunk fields + ``_rerank_score`` when reranking).
        """
        if self._table is None:
            raise RuntimeError("Knowledge store not initialised — call ingest() first.")

        WorkflowLogger.log_stage_start(
            _STAGE,
            {"query": query, "top_k": top_k, "candidate_k": candidate_k, "filters": filters},
        )

        q = self._table.search(query, query_type="hybrid").limit(candidate_k)
        if filters:
            q = q.where(filters)
        candidates: list[dict[str, Any]] = q.to_list()

        WorkflowLogger.log_stage_progress(_STAGE, f"Hybrid search returned {len(candidates)} candidates")

        if not candidates:
            WorkflowLogger.log_stage_complete(_STAGE, {"returned": 0})
            return []

        results = self._rerank(query, candidates, top_k) if use_reranker else candidates[:top_k]
        WorkflowLogger.log_stage_complete(_STAGE, {"returned": len(results)})
        return results

    def _rerank(
        self, query: str, candidates: list[dict[str, Any]], top_k: int
    ) -> list[dict[str, Any]]:
        """Score candidates with a cross-encoder and return the top ``top_k``."""
        pairs = [(query, c["text_for_embedding"]) for c in candidates]
        scores: list[float] = self._cross_encoder.predict(pairs).tolist()

        for candidate, score in zip(candidates, scores):
            candidate["_rerank_score"] = score

        reranked = sorted(candidates, key=lambda c: c["_rerank_score"], reverse=True)

        WorkflowLogger.log_stage_progress(
            _STAGE,
            f"Cross-encoder reranked {len(reranked)} candidates → top {top_k}",
            {"top_score": round(reranked[0]["_rerank_score"], 4) if reranked else None},
        )
        return reranked[:top_k]

    # Utilities    

    def count(self) -> int:
        """Return number of chunk rows currently stored."""
        return self._table.count_rows() if self._table else 0

    @property
    def is_ready(self) -> bool:
        """True if the table exists and has at least one row."""
        return self._table is not None and self.count() > 0
