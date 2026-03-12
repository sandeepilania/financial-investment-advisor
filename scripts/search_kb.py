"""Search the LanceDB knowledge base.

Run:
    poetry run python .\scripts\search_kb.py --query "best ETFs for retirement"
"""

from __future__ import annotations

import argparse

from knowledge_store import KnowledgeStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Search KB in LanceDB")
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results")
    parser.add_argument(
        "--candidate-k",
        type=int,
        default=20,
        help="Candidates before rerank",
    )
    parser.add_argument(
        "--filters",
        default=None,
        help="Optional WHERE clause (e.g. \"risk_profile = 'low'\")",
    )
    parser.add_argument(
        "--no-rerank",
        action="store_true",
        help="Disable cross-encoder reranking",
    )
    args = parser.parse_args()

    ks = KnowledgeStore()
    if not ks.is_ready:
        raise RuntimeError("Knowledge store is empty. Run ingest_kb.py first.")

    results = ks.search(
        args.query,
        top_k=args.top_k,
        candidate_k=args.candidate_k,
        filters=args.filters,
        use_reranker=not args.no_rerank,
    )

    for idx, row in enumerate(results, start=1):
        title = row.get("title")
        category = row.get("category")
        score = row.get("_rerank_score")
        preview = (row.get("content") or "").replace("\n", " ")[:200]
        score_text = f" | rerank={score:.4f}" if score is not None else ""
        print(f"{idx}. {title} [{category}]{score_text}\n   {preview}\n")


if __name__ == "__main__":
    main()
