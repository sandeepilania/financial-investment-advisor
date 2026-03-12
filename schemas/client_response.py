from typing import Optional

from pydantic import BaseModel


class ClientResponse(BaseModel):
    resolved: bool
    follow_up: Optional[str] = None
