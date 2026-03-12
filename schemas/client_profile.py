from typing import List, Optional
from pydantic import BaseModel

class ClientProfile(BaseModel):
    name: str
    age: int
    risk_tolerance: str  # e.g., "low", "medium", "high"
    investment_goals: List[str]  # e.g., ["retirement", "education", "wealth growth"]
    current_investments: Optional[List[str]] = None  # e.g., ["stocks", "bonds"]

