from typing import Optional

from pydantic import BaseModel


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    source_type: str
    doc_id: Optional[str] = None
    category: Optional[str] = None
