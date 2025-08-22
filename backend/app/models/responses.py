from pydantic import BaseModel
from typing import Any, Dict

class TaskAck(BaseModel):
    message: str
    extra: Dict[str, Any] = {}
