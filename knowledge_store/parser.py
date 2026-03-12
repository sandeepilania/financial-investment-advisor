"""Markdown document parsing, metadata inference, chunking, and row building.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any



# Markdown parsing

def parse_markdown_doc(text: str) -> dict[str, Any]:
    """Extract structured fields from a knowledge-base markdown file.

    Expected format::

        Title: <title>
        Category: <category>
        Tags: <tag1>, <tag2>          ← optional
        Risk Profile: <profile>       ← optional
        Target Audience: <audience>   ← optional
        Investor Horizon: <horizon>   ← optional
        Last Updated: <yyyy-mm>       ← optional

        Key Points:
        - <point 1>
        - <point 2>

        Sources:
        - <source 1>

        Content:
        <body text>

    Returns a dict with keys: title, category, tags, content, target_audience,
    investor_horizon, last_updated, key_points, citations.
    """
    def _extract_block(label: str, body: str) -> str:
        pattern = rf"^{label}:\s*(.*?)(?=^\w[\w\s]*?:\s*|\Z)"
        match = re.search(pattern, body, flags=re.MULTILINE | re.DOTALL)
        return match.group(1).strip() if match else ""

    def _parse_bullets(block: str) -> list[str]:
        if not block:
            return []
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        bullets: list[str] = []
        for line in lines:
            if line.startswith("-"):
                bullets.append(line[1:].strip())
            else:
                bullets.append(line)
        return bullets

    title_match = re.search(r"^Title:\s*(.+)$", text, flags=re.MULTILINE)
    category_match = re.search(r"^Category:\s*(.+)$", text, flags=re.MULTILINE)
    tags_match = re.search(r"^Tags:\s*(.+)$", text, flags=re.MULTILINE)
    target_audience_match = re.search(r"^Target Audience:\s*(.+)$", text, flags=re.MULTILINE)
    investor_horizon_match = re.search(r"^Investor Horizon:\s*(.+)$", text, flags=re.MULTILINE)
    last_updated_match = re.search(r"^Last Updated:\s*(.+)$", text, flags=re.MULTILINE)
    content_match = re.search(r"^Content:\s*(.*)$", text, flags=re.MULTILINE | re.DOTALL)

    title = title_match.group(1).strip() if title_match else ""
    category = category_match.group(1).strip() if category_match else ""
    tags_raw = tags_match.group(1).strip() if tags_match else ""
    content = content_match.group(1).strip() if content_match else ""
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []
    target_audience = target_audience_match.group(1).strip() if target_audience_match else ""
    investor_horizon = investor_horizon_match.group(1).strip() if investor_horizon_match else ""
    last_updated = last_updated_match.group(1).strip() if last_updated_match else ""
    key_points_block = _extract_block("Key Points", text)
    sources_block = _extract_block("Sources", text)
    key_points = _parse_bullets(key_points_block)
    citations = _parse_bullets(sources_block)

    return {
        "title": title,
        "category": category,
        "tags": tags,
        "content": content,
        "target_audience": target_audience,
        "investor_horizon": investor_horizon,
        "last_updated": last_updated,
        "key_points": key_points,
        "citations": citations,
    }

# Metadata inference

def infer_risk_profile(title: str, tags: list[str], content: str) -> str | None:
    """Infer a risk level from document text: 'low' | 'moderate' | 'high' | None."""
    hay = " ".join([title, content, " ".join(tags)]).lower()
    if "conservative" in hay or "low-risk" in hay:
        return "low"
    if "balanced" in hay or "moderate-risk" in hay:
        return "moderate"
    if "aggressive" in hay or "high-risk" in hay:
        return "high"
    return None


def infer_target_age_group(title: str, content: str) -> str | None:
    """Infer a target investor age group from document text."""
    hay = f"{title} {content}".lower()
    if "retire" in hay:
        return "retiree"
    if "30s" in hay:
        return "30s"
    if "40s" in hay:
        return "40s+"
    if "20s" in hay:
        return "20s"
    return "general"


def infer_asset_class(category: str, title: str, content: str) -> str | None:
    """Infer an asset class from category, title, and content."""
    hay = f"{title} {content}".lower()
    if "bond" in hay or "treasury" in hay or "fixed-income" in hay:
        return "fixed_income"
    if "stock" in hay or "equity" in hay or "dividend" in hay:
        return "equities"
    if "etf" in hay or "index fund" in hay or "mutual fund" in hay:
        return "funds"
    if "401(k)" in hay or "ira" in hay or "retirement" in hay:
        return "retirement"
    if category == "economics":
        return "macro"
    if category == "market_report":
        return "sector_outlook"
    if category == "investment_strategy":
        return "multi_asset"
    return None



# Chunking

def chunk_content(content: str, max_chars: int = 900) -> list[str]:
    """Paragraph-aware chunking with hard-split fallback for oversized paragraphs.

    Most KB documents are short enough to fit in a single chunk.
    """
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    if not paragraphs:
        return [content.strip()] if content.strip() else []

    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        candidate = f"{current}\n\n{para}".strip() if current else para
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current)
            if len(para) <= max_chars:
                current = para
            else:
                for i in range(0, len(para), max_chars):
                    chunks.append(para[i : i + max_chars].strip())
                current = ""

    if current:
        chunks.append(current)

    return chunks


# Row builders

def build_rows_from_file(path: Path) -> list[dict[str, Any]]:
    """Parse a single markdown file and return LanceDB-ready row dicts."""
    raw = path.read_text(encoding="utf-8")
    parsed = parse_markdown_doc(raw)

    title = parsed["title"]
    category = parsed["category"]
    tags = parsed["tags"]
    content = parsed["content"]
    target_audience = parsed.get("target_audience") or None
    investor_horizon = parsed.get("investor_horizon") or None
    last_updated = parsed.get("last_updated") or None
    key_points = parsed.get("key_points") or []
    citations = parsed.get("citations") or []

    risk_profile = infer_risk_profile(title, tags, content)
    target_age_group = infer_target_age_group(title, content)
    asset_class = infer_asset_class(category, title, content)
    doc_id = f"{category}__{path.stem}"
    chunks = chunk_content(content)

    rows: list[dict[str, Any]] = []
    for idx, chunk in enumerate(chunks):
        text_for_embedding = (
            f"Title: {title}\n"
            f"Category: {category}\n"
            f"Tags: {', '.join(tags) if tags else 'none'}\n"
            f"Risk Profile: {risk_profile or 'unknown'}\n"
            f"Target Audience: {target_audience or 'unknown'}\n"
            f"Investor Horizon: {investor_horizon or 'unknown'}\n"
            f"Last Updated: {last_updated or 'unknown'}\n"
            f"Key Points: {', '.join(key_points) if key_points else 'none'}\n"
            f"Sources: {', '.join(citations) if citations else 'none'}\n"
            f"Target Age Group: {target_age_group or 'unknown'}\n"
            f"Asset Class: {asset_class or 'unknown'}\n\n"
            f"Content:\n{chunk}"
        )
        rows.append(
            {
                "id": f"{doc_id}__chunk_{idx}",
                "doc_id": doc_id,
                "chunk_id": idx,
                "title": title,
                "category": category,
                "tags": tags,
                "risk_profile": risk_profile,
                "target_audience": target_audience,
                "investor_horizon": investor_horizon,
                "last_updated": last_updated,
                "key_points": key_points,
                "citations": citations,
                "target_age_group": target_age_group,
                "asset_class": asset_class,
                "source": "curated_kb",
                "text_for_embedding": text_for_embedding,
                "content": chunk,
            }
        )
    return rows


def load_all_rows(data_dir: Path) -> list[dict[str, Any]]:
    """Walk ``data_dir`` recursively and build rows from every ``*.md`` file."""
    rows: list[dict[str, Any]] = []
    for path in sorted(data_dir.rglob("*.md")):
        rows.extend(build_rows_from_file(path))
    return rows
