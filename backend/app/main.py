from fastapi import FastAPI
from app.core.config import settings
from app.api import health, ingest, search, chat, stats, embeddings, pdf

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

# Mount routers
app.include_router(health.router, tags=["health"])
app.include_router(ingest.router, tags=["ingest"])
app.include_router(search.router, tags=["search"])
app.include_router(chat.router, tags=["chat"])
app.include_router(stats.router, tags=["stats"])
app.include_router(embeddings.router, tags=["embeddings"])
app.include_router(pdf.router, tags=["pdf"])
