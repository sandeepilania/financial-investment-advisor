"""Knowledge store package.

Public API: ``KnowledgeStore``

Modules
-------
knowledge_store.parser   markdown parsing, metadata inference, chunking, row building
knowledge_store.store    KnowledgeStore class (ingest, index, search, rerank)
"""

from knowledge_store.store import KnowledgeStore

__all__ = ["KnowledgeStore"]
