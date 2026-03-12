from typing import List

from pydantic import BaseModel


class Finding(BaseModel):
    detail: str
    sources: List[str]


class AnalystFindings(BaseModel):
    findings: List[Finding]
    assumptions: List[str] = []
    missing_data: List[str] = []
