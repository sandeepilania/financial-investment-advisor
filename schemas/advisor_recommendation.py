from typing import List

from pydantic import BaseModel


class AdvisorRecommendation(BaseModel):
    summary: str
    recommendation: str
    next_steps: List[str]
