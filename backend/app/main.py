from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import httpx
import meilisearch
import redis
from typing import List, Dict, Any

app = FastAPI(title="RAG Backend (CPU)")

MEILI_URL = os.getenv("MEILI_URL", "http://meilisearch:7700")
MEILI_KEY = os.getenv("MEILI_KEY", "")
PROXY_URL = os.getenv("PROXY_URL", "http://litellm:4000")
PROXY_KEY = os.getenv("PROXY_KEY", "")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
INDEX_NAME = os.getenv("MEILI_INDEX", "documents")
CHUNK_INDEX_NAME = os.getenv("MEILI_CHUNK_INDEX", "chunks")
EMBED_DIM = int(os.getenv("EMBED_DIM", "384"))

meili_client = meilisearch.Client(MEILI_URL, MEILI_KEY or None)
r = redis.Redis.from_url(REDIS_URL, decode_responses=False)


class IngestItem(BaseModel):
    id: str
    text: str
    metadata: Dict[str, Any] | None = None


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/ingest")
async def ingest(items: List[IngestItem]):
    index = meili_client.index(INDEX_NAME)
    payload = [
        {"id": it.id, "content": it.text, "metadata": it.metadata or {}} for it in items
    ]
    index.add_documents(payload)
    return {"indexed": len(payload)}


class Query(BaseModel):
    query: str
    k: int = 5


async def get_embedding(text: str) -> List[float]:
    import hashlib
    key = f"emb:{hashlib.sha256(text.encode('utf-8')).hexdigest()}".encode()
    cached = r.get(key)
    if cached:
        return [float(x) for x in cached.decode().split(",")]

    url = f"{PROXY_URL}/embeddings"
    headers = {"Authorization": f"Bearer {PROXY_KEY}"} if PROXY_KEY else {}
    body = {"model": "local-embeddings", "input": text}
    async with httpx.AsyncClient(timeout=60) as client:
        res = await client.post(url, headers=headers, json=body)
        if res.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Embed error: {res.text}")
        vec = res.json()["data"][0]["embedding"]
    r.setex(key, 3600, ",".join(str(x) for x in vec))
    return vec


@app.post("/search")
async def search(q: Query):
    import hashlib
    qkey = f"ans:{hashlib.sha256(q.query.encode('utf-8')).hexdigest()}".encode()
    cached = r.get(qkey)
    if cached:
        return {"cached": True, "answer": cached.decode()}

    query_vec = await get_embedding(q.query)

    index = meili_client.index(INDEX_NAME)
    search_payload = {
        "q": q.query,
        "limit": q.k,
        "vector": {"vector": query_vec, "k": q.k},
    }
    res = index.search(search_payload)
    hits = res.get("hits", [])

    context = "\n\n".join(h.get("content", "") for h in hits)
    prompt = f"You are a helpful assistant. Use the context to answer.\n\nContext:\n{context}\n\nQuestion: {q.query}\nAnswer:"

    url = f"{PROXY_URL}/chat/completions"
    headers = {"Authorization": f"Bearer {PROXY_KEY}"} if PROXY_KEY else {}
    body = {
        "model": "groq-llama3",
        "messages": [
            {"role": "system", "content": "Answer strictly based on context; cite if possible."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    async with httpx.AsyncClient(timeout=120) as client:
        llm_res = await client.post(url, headers=headers, json=body)
        if llm_res.status_code != 200:
            raise HTTPException(status_code=500, detail=f"LLM error: {llm_res.text}")
        answer = llm_res.json()["choices"][0]["message"]["content"]

    r.setex(qkey, 600, answer)

    return {"cached": False, "answer": answer, "hits": hits}


def _ensure_index(uid: str) -> Dict[str, Any]:
    def _wait(task: Dict[str, Any]) -> None:
        task_uid = task.get("taskUid") or task.get("uid")
        if task_uid is not None:
            meili_client.wait_for_task(task_uid)

    # Ensure index exists (wait for async task)
    try:
        meili_client.get_index(uid)
    except meilisearch.errors.MeilisearchApiError:
        t = meili_client.create_index(uid=uid, options={"primaryKey": "id"})
        _wait(t)

    index = meili_client.index(uid)
    # Configure vector embedders and base index settings
    settings_payload = {
        "embedders": {
            "default": {
                "source": "userProvided",
                "dimensions": EMBED_DIM,
            }
        },
        "searchableAttributes": ["content", "title"],
        "displayedAttributes": ["id", "content", "title", "metadata", "source", "tags"],
        "filterableAttributes": ["source", "tags", "metadata.sha", "metadata.lang"],
        "sortableAttributes": ["created_at", "updated_at"],
    }
    t2 = index.update_settings(settings_payload)
    _wait(t2)
    return {"index": uid, "embed_dim": EMBED_DIM}


@app.post("/init-index")
async def init_index():
    res_docs = _ensure_index(INDEX_NAME)
    res_chunks = _ensure_index(CHUNK_INDEX_NAME)
    return {"status": "ok", "documents": res_docs, "chunks": res_chunks}


@app.on_event("startup")
async def _auto_init_meilisearch_index() -> None:
    try:
        await init_index()
    except Exception:
        # Avoid blocking app startup if index already exists or Meili not ready yet
        pass
