from pydantic import BaseModel
from typing import Optional

class HealthResponse(BaseModel):
    status: str
    embeddings_available: bool
    embedding_dimensions: Optional[int] = None
