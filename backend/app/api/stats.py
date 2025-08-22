from fastapi import APIRouter, HTTPException
from app.core.clients import meili_client
from app.core.config import settings
from app.core.logging import logger

router = APIRouter()

@router.get("/stats")
async def stats():
    try:
        doc_idx = meili_client.get_index(settings.MEILI_INDEX)
        chk_idx = meili_client.get_index(settings.CHUNKS_INDEX)

        doc_stats = doc_idx.get_stats()   # Meilisearch returns dicts here
        chk_stats = chk_idx.get_stats()

        return {
            "documents": {
                "count": doc_stats.get("numberOfDocuments"),
                "size": doc_stats.get("rawDocumentDbSize"),
                "indexing": doc_stats.get("isIndexing"),
            },
            "chunks": {
                "count": chk_stats.get("numberOfDocuments"),
                "size": chk_stats.get("rawDocumentDbSize"),
                "indexing": chk_stats.get("isIndexing"),
                "embeddings": chk_stats.get("numberOfEmbeddedDocuments"),
            },
        }
    except Exception as e:
        logger.error(f"stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
