from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import httpx
import meilisearch
import redis
import hashlib
import json
import os
import re
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RAGOPS API",
    description="Production-Ready RAG Pipeline with Chunking and Embeddings",
    version="2.0.0"
)

# Configuration
MEILI_URL = os.getenv("MEILI_URL", "http://meilisearch:7700")
MEILI_KEY = os.getenv("MEILI_KEY", "your_master_key_here")
PROXY_URL = os.getenv("PROXY_URL", "http://litellm:4000")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
MEILI_INDEX = os.getenv("MEILI_INDEX", "documents")
CHUNKS_INDEX = "chunks"
EMBED_DIM = int(os.getenv("EMBED_DIM", "384"))

# Initialize clients
meili_client = meilisearch.Client(MEILI_URL, MEILI_KEY)
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# Pydantic models
class Document(BaseModel):
    id: str
    text: str
    metadata: Optional[Dict[str, Any]] = {}

class SearchRequest(BaseModel):
    query: str
    k: int = 5
    use_embeddings: Optional[bool] = True  # New: Enable/disable vector search

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.2
    model: Optional[str] = "groq-llama3"

class HealthResponse(BaseModel):
    status: str
    embeddings_available: bool
    embedding_dimensions: Optional[int] = None
    embedding_dimensions: Optional[int] = None

class SearchResponse(BaseModel):
    answer: str
    chunks: List[Dict[str, Any]]
    total_chunks_found: int
    cached: bool
    search_method: str  # New: "text", "vector", or "hybrid"

# Embedding utilities
async def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings using LiteLLM (TEI backend)"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Check cache first
            cached_embeddings = []
            uncached_texts = []
            uncached_indices = []
            
            for i, text in enumerate(texts):
                cache_key = f"embedding:{hashlib.md5(text.encode()).hexdigest()}"
                cached = redis_client.get(cache_key)
                if cached:
                    cached_embeddings.append((i, json.loads(cached)))
                else:
                    uncached_texts.append(text)
                    uncached_indices.append(i)
            
            # Generate embeddings for uncached texts via LiteLLM
            new_embeddings = []
            if uncached_texts:
                response = await client.post(
                    f"{PROXY_URL}/v1/embeddings",
                    json={
                        "model": "local-embeddings",
                        "input": uncached_texts
                    },
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    for i, embedding_data in enumerate(result["data"]):
                        # Handle LiteLLM embedding format: {"embedding": {"default": [array]}}
                        embedding_raw = embedding_data.get("embedding", embedding_data)
                        if isinstance(embedding_raw, dict) and "default" in embedding_raw:
                            embedding = embedding_raw["default"]
                        elif isinstance(embedding_raw, list):
                            embedding = embedding_raw
                        else:
                            logger.warning(f"Unexpected embedding format: {type(embedding_raw)}")
                            embedding = embedding_raw
                        new_embeddings.append((uncached_indices[i], embedding))
                        
                        # Cache the embedding for 1 hour
                        text = uncached_texts[i]
                        cache_key = f"embedding:{hashlib.md5(text.encode()).hexdigest()}"
                        redis_client.setex(cache_key, 3600, json.dumps(embedding))
                else:
                    logger.error(f"Embedding generation failed: {response.status_code} - {response.text}")
                    return []
            
            # Combine cached and new embeddings in correct order
            all_embeddings = [None] * len(texts)
            for idx, embedding in cached_embeddings + new_embeddings:
                all_embeddings[idx] = embedding
            
            return [emb for emb in all_embeddings if emb is not None]
            
    except Exception as e:
        logger.error(f"Error generating embeddings: {str(e)}")
        return []

# Chunking utility functions
def chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
    """Split text into overlapping chunks"""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence endings within the last 100 characters
            last_part = text[max(start, end-100):end]
            sentence_end = max(
                last_part.rfind('.'),
                last_part.rfind('!'),
                last_part.rfind('?')
            )
            
            if sentence_end > -1:
                end = max(start, end-100) + sentence_end + 1
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = end - overlap
        
        # Prevent infinite loop
        if start >= len(text):
            break
    
    return chunks

# Health check with embeddings status
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check including embeddings availability"""
    embeddings_available = False
    try:
        # Test embeddings via LiteLLM
        test_embeddings = await generate_embeddings(["test"])
        embeddings_available = len(test_embeddings) > 0 and len(test_embeddings[0]) == EMBED_DIM
    except Exception as e:
        logger.warning(f"Embeddings health check failed: {e}")
    
    return HealthResponse(
        status="healthy",
        embeddings_available=embeddings_available,
        embedding_dimensions=EMBED_DIM if embeddings_available else None
    )

# Initialize indexes with embeddings support
@app.post("/init-index")
async def initialize_index():
    """Initialize Meilisearch indexes with embeddings support"""
    try:
        # Create documents index (text search only)
        try:
            index = meili_client.get_index(MEILI_INDEX)
        except:
            index = meili_client.create_index(MEILI_INDEX, {'primaryKey': 'id'})
        
        # Configure documents index (no embeddings)
        index.update_searchable_attributes(['text', 'title', 'content'])
        index.update_filterable_attributes(['category', 'tags', 'author', 'source'])
        
        # Create chunks index with embeddings support
        try:
            chunks_index = meili_client.get_index(CHUNKS_INDEX)
        except:
            chunks_index = meili_client.create_index(CHUNKS_INDEX, {'primaryKey': 'id'})
        
        # Configure chunks index with vector search
        chunks_index.update_searchable_attributes(['text', 'title', 'content'])
        chunks_index.update_filterable_attributes(['document_id', 'category', 'tags', 'chunk_index'])
        
        # Configure embeddings for chunks index
        chunks_index.update_settings({
            'embedders': {
                'default': {
                    'source': 'userProvided',
                    'dimensions': EMBED_DIM
                }
            }
        })
        
        return {
            "message": "Indexes initialized successfully with embeddings support",
            "indexes": [MEILI_INDEX, CHUNKS_INDEX],
            "embedding_dimensions": EMBED_DIM
        }
    except Exception as e:
        logger.error(f"Error initializing indexes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Document ingestion with chunking and embeddings
@app.post("/ingest")
async def ingest_documents(documents: List[Document]):
    """Ingest documents with automatic chunking and embedding generation"""
    try:
        doc_index = meili_client.get_index(MEILI_INDEX)
        chunks_index = meili_client.get_index(CHUNKS_INDEX)
        
        # Process documents
        processed_docs = []
        processed_chunks = []
        all_chunk_texts = []  # For batch embedding generation
        
        for doc in documents:
            # Process whole document
            processed_doc = {
                "id": doc.id,
                "text": doc.text,
                "content": doc.text,  # Alias for searchability
                **doc.metadata,
                "indexed_at": datetime.now().isoformat(),
                "chunk_count": 0  # Will be updated
            }
            
            # Create chunks from document
            chunks = chunk_text(doc.text, chunk_size=512, overlap=50)
            processed_doc["chunk_count"] = len(chunks)
            
            for i, chunk_content in enumerate(chunks):
                chunk_id = f"{doc.id}-chunk-{i}"
                processed_chunk = {
                    "id": chunk_id,
                    "text": chunk_content,
                    "content": chunk_content,
                    "document_id": doc.id,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    **doc.metadata,  # Inherit document metadata
                    "indexed_at": datetime.now().isoformat()
                }
                processed_chunks.append(processed_chunk)
                all_chunk_texts.append(chunk_content)
            
            processed_docs.append(processed_doc)
        
        # Generate embeddings for all chunks via LiteLLM
        logger.info(f"Generating embeddings for {len(all_chunk_texts)} chunks...")
        embeddings = await generate_embeddings(all_chunk_texts)
        
        if len(embeddings) == len(all_chunk_texts):
            # Add embeddings to chunks
            for i, chunk in enumerate(processed_chunks):
                chunk["_vectors"] = {"default": embeddings[i]}
            logger.info(f"✅ Generated {len(embeddings)} embeddings via LiteLLM")
        else:
            logger.warning(f"⚠️ Embedding count mismatch: {len(embeddings)} vs {len(all_chunk_texts)}")
            # Fallback: Add null vectors to opt out of vector search
            for chunk in processed_chunks:
                chunk["_vectors"] = {"default": None}
        
        # Add to Meilisearch indexes
        doc_task = doc_index.add_documents(processed_docs)
        chunk_task = chunks_index.add_documents(processed_chunks) if processed_chunks else None
        
        return {
            "indexed": len(processed_docs),
            "chunks_created": len(processed_chunks),
            "embeddings_generated": len(embeddings),
            "document_task": doc_task,
            "chunk_task": chunk_task
        }
    
    except Exception as e:
        logger.error(f"Error ingesting documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Simple search (direct Meilisearch on documents - text only)
@app.post("/search-direct")
async def search_direct(request: SearchRequest):
    """Direct search without LLM generation (text search only)"""
    # Validation
    if not request.query or request.query.strip() == '':
        raise HTTPException(status_code=422, detail="Query cannot be empty")
    if request.k <= 0:
        raise HTTPException(status_code=422, detail="k must be greater than 0")
        
    try:
        index = meili_client.get_index(MEILI_INDEX)
        
        # Simple text search
        search_results = index.search(
            request.query,
            {
                'limit': request.k,
                'attributesToRetrieve': ['*'],
                'attributesToHighlight': ['text', 'content']
            }
        )
        
        return {
            "hits": search_results['hits'],
            "total": search_results['estimatedTotalHits'],
            "query": request.query,
            "index_used": "documents",
            "search_method": "text"
        }
    
    except Exception as e:
        logger.error(f"Error in direct search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Chunk-based search with optional vector search
@app.post("/search-chunks")
async def search_chunks(request: SearchRequest):
    """Direct search on chunks with optional vector search"""
    # Validation
    if not request.query or request.query.strip() == '':
        raise HTTPException(status_code=422, detail="Query cannot be empty")
    if request.k <= 0:
        raise HTTPException(status_code=422, detail="k must be greater than 0")
        
    try:
        chunks_index = meili_client.get_index(CHUNKS_INDEX)
        search_method = "text"
        
        # Try vector search first if embeddings are enabled
        if request.use_embeddings:
            try:
                # Generate query embedding
                query_embeddings = await generate_embeddings([request.query])
                if query_embeddings:
                    query_vector = query_embeddings[0]
                    # Ensure query_vector is a clean array, not nested object
                    if isinstance(query_vector, dict) and "default" in query_vector:
                        query_vector = query_vector["default"]
                    
                    # Vector search
                    search_results = chunks_index.search(
                        request.query,
                        {
                            'vector': query_vector,
                            'hybrid': {
                                'semanticRatio': 0.8,  # 80% vector, 20% text
                                'embedder': 'default'
                            },
                            'limit': request.k,
                            'attributesToRetrieve': ['*']
                        }
                    )
                    search_method = "hybrid"
                    logger.info("✅ Using hybrid vector + text search")
                else:
                    # Fallback to text search
                    search_results = chunks_index.search(
                        request.query,
                        {
                            'limit': request.k,
                            'attributesToRetrieve': ['*'],
                            'attributesToHighlight': ['text', 'content']
                        }
                    )
                    search_method = "text"
                    logger.info("⚠️ Embeddings failed, using text search")
            except Exception as vector_error:
                logger.warning(f"Vector search failed: {vector_error}, falling back to text")
                # Fallback to text search
                search_results = chunks_index.search(
                    request.query,
                    {
                        'limit': request.k,
                        'attributesToRetrieve': ['*'],
                        'attributesToHighlight': ['text', 'content']
                    }
                )
                search_method = "text"
        else:
            # Text search only
            search_results = chunks_index.search(
                request.query,
                {
                    'limit': request.k,
                    'attributesToRetrieve': ['*'],
                    'attributesToHighlight': ['text', 'content']
                }
            )
            search_method = "text"
        
        return {
            "hits": search_results['hits'],
            "total": search_results['estimatedTotalHits'],
            "query": request.query,
            "index_used": "chunks",
            "search_method": search_method
        }
    
    except Exception as e:
        logger.error(f"Error in chunk search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# RAG Search with LLM (now using chunks with embeddings)
@app.post("/search", response_model=SearchResponse)
async def rag_search(request: SearchRequest):
    """RAG search with chunk-based retrieval, embeddings, and LLM generation"""
    # Validation
    if not request.query or request.query.strip() == '':
        raise HTTPException(status_code=422, detail="Query cannot be empty")
    if request.k <= 0:
        raise HTTPException(status_code=422, detail="k must be greater than 0")
    
    try:
        # Create cache key
        cache_key = f"rag:{hashlib.md5(f'{request.query}:{request.k}:{request.use_embeddings}'.encode()).hexdigest()}"
        
        # Check cache
        cached_result = redis_client.get(cache_key)
        if cached_result:
            result = json.loads(cached_result)
            result["cached"] = True
            return SearchResponse(**result)
        
        # Search chunks using the chunk search endpoint logic
        chunks_index = meili_client.get_index(CHUNKS_INDEX)
        search_method = "text"
        
        # Try vector search first if embeddings are enabled
        if request.use_embeddings:
            try:
                # Generate query embedding via LiteLLM
                query_embeddings = await generate_embeddings([request.query])
                if query_embeddings:
                    query_vector = query_embeddings[0]
                    
                    # Hybrid vector + text search
                    search_results = chunks_index.search(
                        request.query,
                        {
                            'vector': {'default': query_vector},
                            'hybrid': {
                                'semanticRatio': 0.8,  # 80% semantic, 20% keyword
                                'embedder': 'default'
                            },
                            'limit': request.k * 2,  # Get more for better selection
                            'attributesToRetrieve': ['*']
                        }
                    )
                    search_method = "hybrid"
                    logger.info("✅ RAG using hybrid vector + text search")
                else:
                    # Fallback to text search
                    search_results = chunks_index.search(
                        request.query,
                        {
                            'limit': request.k * 2,
                            'attributesToRetrieve': ['*']
                        }
                    )
                    search_method = "text"
            except Exception as vector_error:
                logger.warning(f"RAG vector search failed: {vector_error}")
                # Fallback to text search
                search_results = chunks_index.search(
                    request.query,
                    {
                        'limit': request.k * 2,
                        'attributesToRetrieve': ['*']
                    }
                )
                search_method = "text"
        else:
            # Text search only
            search_results = chunks_index.search(
                request.query,
                {
                    'limit': request.k * 2,
                    'attributesToRetrieve': ['*']
                }
            )
            search_method = "text"
        
        hits = search_results.get('hits', [])
        
        if not hits:
            result = {
                "answer": "I couldn't find any relevant chunks to answer your question.",
                "chunks": [],
                "total_chunks_found": 0,
                "cached": False,
                "search_method": search_method
            }
            return SearchResponse(**result)
        
        # Process chunks and deduplicate by document if needed
        unique_chunks = []
        for hit in hits:
            doc_id = hit.get('document_id', 'unknown')
            # Take up to 2 chunks per document to avoid overwhelming context
            doc_chunk_count = sum(1 for chunk in unique_chunks if chunk.get('document_id') == doc_id)
            
            if doc_chunk_count < 2:  # Limit chunks per document
                unique_chunks.append(hit)
            
            if len(unique_chunks) >= request.k:
                break
        
        # Prepare context for LLM
        context_parts = []
        chunks = []
        
        for i, hit in enumerate(unique_chunks):
            # Try different field names for content
            content = hit.get('content', hit.get('text', ''))
            title = hit.get('title', hit.get('metadata', {}).get('title', f"Chunk {i+1}"))
            doc_id = hit.get('document_id', f'doc-{i}')
            chunk_idx = hit.get('chunk_index', i)
            
            if content:  # Only add if we have content
                context_parts.append(f"Document: {title} (Chunk {chunk_idx})\nContent: {content}\n")
                
                chunks.append({
                    "id": hit.get('id', f'chunk-{i}'),
                    "document_id": doc_id,
                    "chunk_index": chunk_idx,
                    "content": content[:300] + "..." if len(content) > 300 else content,
                    "metadata": {k: v for k, v in hit.items() if k not in ['text', 'content', '_vectors']}
                })
        
        if not chunks:
            result = {
                "answer": "I found chunks but couldn't extract readable content from them.",
                "chunks": [],
                "total_chunks_found": len(hits),
                "cached": False,
                "search_method": search_method
            }
            return SearchResponse(**result)
        
        context = "\n".join(context_parts)
        
        # Generate LLM response via LiteLLM
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                llm_payload = {
                    "model": "groq-llama3",
                    "messages": [
                        {
                            "role": "system",
                            "content": f"You are a helpful AI assistant. Answer the user's question based on the provided document chunks. The search used {search_method} method. If the chunks don't contain enough information, say so clearly. Synthesize information from multiple chunks when relevant."
                        },
                        {
                            "role": "user", 
                            "content": f"Context from document chunks:\n{context}\n\nQuestion: {request.query}\n\nPlease provide a comprehensive answer based on the context above."
                        }
                    ],
                    "temperature": 0.3,
                    "max_tokens": 500
                }
                
                response = await client.post(
                    f"{PROXY_URL}/v1/chat/completions",
                    json=llm_payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    llm_result = response.json()
                    answer = llm_result['choices'][0]['message']['content']
                else:
                    logger.error(f"LLM request failed: {response.status_code} - {response.text}")
                    answer = "I found relevant document chunks but couldn't generate a response at the moment."
                    
        except Exception as llm_error:
            logger.error(f"LLM generation error: {str(llm_error)}")
            answer = "I found relevant document chunks but couldn't generate a response due to a technical issue."
        
        # Prepare result
        result = {
            "answer": answer,
            "chunks": chunks,
            "total_chunks_found": len(hits),
            "cached": False,
            "search_method": search_method
        }
        
        # Cache the result for 10 minutes
        try:
            redis_client.setex(cache_key, 600, json.dumps({
                "answer": result["answer"],
                "chunks": result["chunks"], 
                "total_chunks_found": result["total_chunks_found"],
                "search_method": result["search_method"]
            }))
        except Exception as cache_error:
            logger.warning(f"Cache write failed: {str(cache_error)}")
        
        return SearchResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in RAG search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Direct chat
@app.post("/chat")
async def chat(request: ChatRequest):
    """Direct chat with LLM without document retrieval"""
    # Validation
    if not request.messages or len(request.messages) == 0:
        raise HTTPException(status_code=422, detail="Messages cannot be empty")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            llm_payload = {
                "model": request.model,
                "messages": [{"role": msg.role, "content": msg.content} for msg in request.messages],
                "temperature": request.temperature,
                "max_tokens": 1000
            }
            
            response = await client.post(
                f"{PROXY_URL}/v1/chat/completions",
                json=llm_payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Chat request failed: {response.status_code} - {response.text}")
                raise HTTPException(status_code=502, detail="LLM service unavailable")
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Index statistics
@app.get("/stats")
async def get_index_stats():
    """Get statistics for both indexes"""
    try:
        doc_index = meili_client.get_index(MEILI_INDEX)
        chunks_index = meili_client.get_index(CHUNKS_INDEX)
        
        doc_stats = doc_index.get_stats()
        chunk_stats = chunks_index.get_stats()
        
        return {
            "documents": {
                "count": doc_stats.numberOfDocuments,
                "size": doc_stats.rawDocumentDbSize,
                "indexing": doc_stats.isIndexing
            },
            "chunks": {
                "count": chunk_stats.numberOfDocuments, 
                "size": chunk_stats.rawDocumentDbSize,
                "indexing": chunk_stats.isIndexing,
                "embeddings": chunk_stats.numberOfEmbeddedDocuments
            },
            "embedding_dimensions": EMBED_DIM
        }
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Test embeddings endpoint
@app.post("/test-embeddings")
async def test_embeddings_endpoint(texts: List[str]):
    """Test embeddings generation via LiteLLM"""
    try:
        embeddings = await generate_embeddings(texts)
        return {
            "input_count": len(texts),
            "embeddings_generated": len(embeddings),
            "dimensions": len(embeddings[0]) if embeddings else 0,
            "sample_embedding": embeddings[0][:5] if embeddings else None
        }
    except Exception as e:
        logger.error(f"Embeddings test failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize system on startup"""
    try:
        # Test connections
        meili_client.health()
        redis_client.ping()
        
        # Test embeddings
        embeddings_working = False
        try:
            test_embeddings = await generate_embeddings(["startup test"])
            embeddings_working = len(test_embeddings) > 0
        except:
            pass
        
        # Initialize indexes
        await initialize_index()
        
        logger.info(f"RAGOPS backend started successfully with Phase 2: Chunking + Embeddings")
        logger.info(f"✅ Embeddings via LiteLLM: {'Working' if embeddings_working else 'Failed'}")
        logger.info(f"✅ Vector dimensions: {EMBED_DIM}")
        
    except Exception as e:
        logger.error(f"Startup error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
