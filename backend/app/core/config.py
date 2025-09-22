import os

class Settings:
    APP_NAME: str = "RAGOPS API"
    APP_VERSION: str = "2.0.0"

    MEILI_URL: str = os.getenv("MEILI_URL", "http://meilisearch:7700")
    MEILI_KEY: str = os.getenv("MEILI_KEY", "your_master_key_here")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379")
    PROXY_URL: str = os.getenv("PROXY_URL", "http://litellm:4000")
    PROXY_KEY: str = os.getenv("PROXY_KEY", "")           

    MEILI_INDEX: str = os.getenv("MEILI_INDEX", "documents")
    CHUNKS_INDEX: str = "chunks"
    EMBED_DIM: int = int(os.getenv("EMBED_DIM", "384"))

settings = Settings()
