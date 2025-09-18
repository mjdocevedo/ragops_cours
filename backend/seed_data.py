import os
import httpx
import hashlib
from typing import Iterable, Dict, Any

API_URL = os.getenv("API_URL", "http://backend:8000")


def iter_docs() -> Iterable[Dict[str, Any]]:
    """Create sample documents with more detailed content"""
    documents = [
        {
            "id": "meilisearch-guide", 
            "text": "Meilisearch is a powerful, fast, and easy-to-use search engine built for modern applications. It supports both traditional full-text search with BM25 ranking and modern vector search capabilities for semantic similarity matching. Meilisearch provides instant search results with typo tolerance, filtering, faceting, and geo-search features. It can handle millions of documents while maintaining sub-millisecond response times.",
            "metadata": {
                "title": "Meilisearch Search Engine Guide",
                "source": "meilisearch-docs.md",
                "category": "search-technology",
                "tags": ["search", "database", "full-text"],
                "sha": "meili123"
            }
        },
        {
            "id": "tei-embeddings-guide",
            "text": "Text Embeddings Inference (TEI) is a comprehensive toolkit for deploying and serving Large Language Model embeddings in production environments. TEI enables high-performance extraction of sentence embeddings from text input, making it ideal for semantic search, recommendation systems, and similarity matching applications. The toolkit supports popular embedding models like sentence-transformers and can run efficiently on both CPU and GPU hardware using optimized implementations from Hugging Face.",
            "metadata": {
                "title": "TEI Embeddings Service Guide", 
                "source": "tei-docs.md",
                "category": "ai-ml",
                "tags": ["embeddings", "ai", "nlp", "huggingface"],
                "sha": "tei456"
            }
        },
        {
            "id": "litellm-proxy-guide",
            "text": "LiteLLM Proxy is a unified interface for multiple language models that simplifies AI application development. It provides a consistent API that can route requests to different LLM providers like Groq, OpenAI, Anthropic, and others, making it easy to switch between providers without changing application code. LiteLLM includes features like load balancing, fallback mechanisms, cost tracking, and request caching. For embeddings, it can be configured to route requests to Text Embeddings Inference (TEI) servers running locally or in the cloud.",
            "metadata": {
                "title": "LiteLLM Proxy Integration Guide",
                "source": "litellm-docs.md", 
                "category": "ai-infrastructure",
                "tags": ["llm", "proxy", "api", "integration"],
                "sha": "lite789"
            }
        },
        {
            "id": "rag-architecture-guide",
            "text": "Retrieval-Augmented Generation (RAG) is a powerful AI architecture that combines information retrieval with language generation. RAG systems work by first retrieving relevant documents or passages from a knowledge base using semantic search, then using those retrieved documents as context for a large language model to generate accurate, grounded responses. This approach helps reduce hallucinations and provides more factual, up-to-date information compared to using LLMs alone.",
            "metadata": {
                "title": "RAG Architecture Overview",
                "source": "rag-guide.md",
                "category": "ai-architecture", 
                "tags": ["rag", "ai", "retrieval", "generation"],
                "sha": "rag101"
            }
        },
        {
            "id": "docker-deployment-guide",
            "text": "Docker containerization provides isolated, reproducible environments for deploying complex applications. With Docker Compose, you can orchestrate multi-service applications using simple YAML configuration files. This makes it easy to deploy RAG pipelines with multiple components like search engines, embedding services, and API backends. Docker ensures consistent deployment across different environments while simplifying scaling and maintenance.",
            "metadata": {
                "title": "Docker Deployment Best Practices",
                "source": "docker-guide.md",
                "category": "devops",
                "tags": ["docker", "deployment", "containers", "orchestration"],
                "sha": "dock999"
            }
        }
    ]
    
    for doc in documents:
        # Add computed hash if not provided
        if not doc["metadata"].get("sha"):
            doc["metadata"]["sha"] = hashlib.sha256(doc["text"].encode()).hexdigest()[:16]
        yield doc


async def main():
    """Ingest sample documents into the RAG system"""
    print("🚀 Starting document ingestion...")
    
    items = list(iter_docs())
    print(f"📄 Prepared {len(items)} documents for ingestion")
    
    async with httpx.AsyncClient(timeout=120) as client:
        try:
            # Ingest documents using the working endpoint
            payload = [
                {
                    "id": doc["id"], 
                    "text": doc["text"], 
                    "metadata": doc["metadata"]
                } 
                for doc in items
            ]
            
            print(f"📤 Sending documents to {API_URL}/ingest...")
            res = await client.post(f"{API_URL}/ingest", json=payload)
            res.raise_for_status()
            result = res.json()
            
            print(f"✅ Successfully ingested {result.get('indexed', 0)} documents!")
            
            # Show what was ingested
            print("\n📋 Ingested documents:")
            for doc in items:
                print(f"   • {doc['id']}: {doc['metadata']['title']}")
                
            print(f"\n🔍 You can now search these documents using:")
            print(f"   • API: POST {API_URL.replace('backend:8000', 'localhost:18000')}/search")
            print(f"   • Web UI: http://localhost:18000/docs")
            
        except httpx.HTTPStatusError as e:
            print(f"❌ HTTP Error {e.response.status_code}: {e.response.text}")
            raise
        except Exception as e:
            print(f"❌ Error during ingestion: {e}")
            raise


if __name__ == "__main__":
    import anyio
    anyio.run(main)
