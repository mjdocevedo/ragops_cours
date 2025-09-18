from pydantic import BaseModel
from typing import Dict, Any, Optional

class Document(BaseModel):
    id: str
    text: str
    metadata: Optional[Dict[str, Any]] = {}
