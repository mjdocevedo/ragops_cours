import os
import httpx
import hashlib
from typing import Iterable, Dict, Any

API_URL = os.getenv("API_URL", "http://backend:8000")


def iter_docs() -> Iterable[Dict[str, Any]]:
    texts = [
        ("doc-1", "Meilisearch is a fast search engine with vector and BM25."),
        ("doc-2", "Text Embeddings Inference (TEI) runs on CPU via Hugging Face."),
        ("doc-3", "LiteLLM Proxy routes to Groq for chat and to TEI for embeddings."),
    ]
    for doc_id, text in texts:
        yield {"id": doc_id, "text": text, "metadata": {"sha": hashlib.sha256(text.encode()).hexdigest()}}


async def main():
    items = list(iter_docs())
    async with httpx.AsyncClient(timeout=120) as client:
        res = await client.post(f"{API_URL}/ingest", json=[
            {"id": it["id"], "text": it["text"], "metadata": it["metadata"]} for it in items
        ])
        res.raise_for_status()
        print(res.json())


if __name__ == "__main__":
    import anyio
    anyio.run(main)
