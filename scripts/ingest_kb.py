"""Ingest markdown knowledge base into LanceDB.

Run:
    poetry run python .\scripts\ingest_kb.py
"""

from __future__ import annotations

import argparse

from knowledge_store import KnowledgeStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest KB docs into LanceDB")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Rebuild the table even if it already exists",
    )
    args = parser.parse_args()

    ks = KnowledgeStore()
    ks.ingest(overwrite=args.overwrite)

    print(f"Ingestion complete. Rows: {ks.count()}")


if __name__ == "__main__":
    main()
