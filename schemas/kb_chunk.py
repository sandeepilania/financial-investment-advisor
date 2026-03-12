"""LanceDB schema for knowledge-base chunks.

The embedding model is initialised once at import time.  LanceDB uses the
SourceField / VectorField descriptors to auto-embed ``text_for_embedding``
whenever rows are added to the table.
"""

from __future__ import annotations

from lancedb.embeddings import get_registry
from lancedb.pydantic import LanceModel, Vector

from core.constants import KB_EMBEDDING_MODEL


# Embedding model — shared by all KBChunk instances
embed_model = (
    get_registry()
    .get("sentence-transformers")
    .create(name=KB_EMBEDDING_MODEL)
)



# LanceDB row schema
class KBChunk(LanceModel):
    """A single chunk of a knowledge-base document stored in LanceDB.

    Fields
    ------
    id                  Globally unique chunk identifier  "<doc_id>__chunk_<n>"
    doc_id              Parent document identifier  "<category>__<stem>"
    chunk_id            Zero-based position of this chunk within the document
    title               Document title extracted from the markdown header
    category            Top-level category folder  (e.g. "economics", "market_report")
    tags                Keyword tags parsed from the markdown header
    risk_profile        Inferred risk level: "low" | "moderate" | "high" | None
    target_audience     Document target audience (e.g. "beginner")
    investor_horizon    Time horizon (e.g. "short" | "long")
    last_updated        Document freshness tag (e.g. "2026-03")
    key_points          Extracted key bullet points
    citations           Source citations
    target_age_group    Inferred audience: "20s" | "30s" | "40s+" | "retiree" | "general"
    asset_class         Inferred asset class (e.g. "equities", "fixed_income")
    source              Provenance tag — always "curated_kb" for this dataset
    text_for_embedding  Rich context string used for both vector and FTS indexing
    vector              Dense embedding produced by ``embed_model`` (auto-populated)
    content             Raw chunk text returned to callers
    """

    id: str
    doc_id: str
    chunk_id: int

    title: str
    category: str
    tags: list[str]
    risk_profile: str | None
    target_audience: str | None
    investor_horizon: str | None
    last_updated: str | None
    key_points: list[str]
    citations: list[str]
    target_age_group: str | None
    asset_class: str | None
    source: str

    # LanceDB will call embed_model to populate `vector` from this field
    text_for_embedding: str = embed_model.SourceField()
    vector: Vector(embed_model.ndims()) = embed_model.VectorField()  # type: ignore[valid-type]

    content: str
