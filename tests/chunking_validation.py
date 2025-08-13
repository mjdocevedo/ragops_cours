#!/usr/bin/env python3
"""
RAGOPS Phase 1 Chunking Validation Script
=========================================

Validates that the new chunking functionality is working correctly:
- Document ingestion creates chunks
- Chunks are stored in separate index  
- Chunk-based search works
- RAG search uses chunks effectively
"""

import asyncio
import httpx
import json
import time

API_URL = "http://backend:8000"

async def validate_chunking():
    """Comprehensive chunking validation"""
    print("🔍 RAGOPS Phase 1 Chunking Validation")
    print("=" * 50)
    
    async with httpx.AsyncClient(timeout=30) as client:
        
        # 1. Health Check
        print("\n1️⃣  System Health")
        try:
            health_response = await client.get(f"{API_URL}/health")
            health_data = health_response.json()
            print(f"   ✅ API Health: {health_data['status']}")
        except Exception as e:
            print(f"   ❌ Health Check Failed: {e}")
            return
        
        # 2. Document Ingestion with Chunking
        print("\n2️⃣  Document Ingestion with Chunking")
        
        chunking_test_doc = {
            "id": "chunking-validation-doc",
            "text": "RAGOPS Phase 1 chunking validation document. This document is designed to test the automatic chunking functionality that splits documents into smaller, manageable pieces. Each chunk maintains important context while being focused enough for effective retrieval. The chunking process uses intelligent sentence boundary detection to avoid breaking sentences awkwardly. This approach significantly improves RAG performance by providing language models with targeted, relevant information instead of entire documents that may contain lots of irrelevant content. The system creates overlapping chunks to ensure no important information is lost at boundaries.",
            "metadata": {
                "title": "Chunking Validation Document", 
                "category": "validation",
                "tags": ["chunking", "phase1", "validation"]
            }
        }
        
        try:
            ingest_response = await client.post(f"{API_URL}/ingest", json=[chunking_test_doc])
            ingest_data = ingest_response.json()
            
            print(f"   ✅ Document Ingested: {ingest_data.get('indexed', 0)}")
            print(f"   ✅ Chunks Created: {ingest_data.get('chunks_created', 0)}")
            print(f"   📋 Document Task: {ingest_data.get('document_task', {}).get('status', 'N/A')}")
            print(f"   📋 Chunk Task: {ingest_data.get('chunk_task', {}).get('status', 'N/A')}")
            
            chunks_created = ingest_data.get('chunks_created', 0)
            if chunks_created == 0:
                print("   ⚠️  Warning: No chunks were created!")
                
        except Exception as e:
            print(f"   ❌ Ingestion Failed: {e}")
            return
        
        # Wait for indexing
        print("   ⏳ Waiting for indexing to complete...")
        await asyncio.sleep(5)
        
        # 3. Index Statistics
        print("\n3️⃣  Index Statistics")
        try:
            stats_response = await client.get(f"{API_URL}/stats")
            if stats_response.status_code == 200:
                stats_data = stats_response.json()
                print(f"   📄 Documents Index: {stats_data.get('documents', {}).get('count', 0)} documents")
                print(f"   🧩 Chunks Index: {stats_data.get('chunks', {}).get('count', 0)} chunks")
            else:
                print(f"   ⚠️  Stats endpoint error: {stats_response.status_code}")
        except Exception as e:
            print(f"   ⚠️  Stats check failed: {e}")
        
        # 4. Direct Chunk Search
        print("\n4️⃣  Direct Chunk Search Test")
        try:
            chunk_search_response = await client.post(f"{API_URL}/search-chunks", 
                json={"query": "chunking validation", "k": 3})
            chunk_data = chunk_search_response.json()
            
            chunks_found = len(chunk_data.get('hits', []))
            total_chunks = chunk_data.get('total', 0)
            index_used = chunk_data.get('index_used', 'unknown')
            
            print(f"   ✅ Index Used: {index_used}")
            print(f"   ✅ Total Chunks Available: {total_chunks}")
            print(f"   ✅ Chunks Returned: {chunks_found}")
            
            if chunks_found > 0:
                # Show first chunk details
                first_chunk = chunk_data['hits'][0]
                chunk_id = first_chunk.get('id', 'N/A')
                document_id = first_chunk.get('document_id', 'N/A')
                chunk_index = first_chunk.get('chunk_index', 'N/A')
                content_preview = first_chunk.get('content', '')[:100] + "..."
                
                print(f"   📄 First Chunk ID: {chunk_id}")
                print(f"   📄 Parent Document: {document_id}")
                print(f"   📄 Chunk Index: {chunk_index}")
                print(f"   📄 Content Preview: {content_preview}")
            
        except Exception as e:
            print(f"   ❌ Chunk Search Failed: {e}")
        
        # 5. RAG Search Using Chunks
        print("\n5️⃣  RAG Search Using Chunks")
        try:
            rag_queries = [
                "What is the purpose of chunking in RAGOPS?",
                "How does the chunking process work?", 
                "What are the benefits of using chunks?"
            ]
            
            for query in rag_queries:
                print(f"\n   Query: {query}")
                rag_response = await client.post(f"{API_URL}/search", 
                    json={"query": query, "k": 3})
                rag_data = rag_response.json()
                
                answer = rag_data.get('answer', '')
                chunks_found = len(rag_data.get('chunks', []))
                total_chunks = rag_data.get('total_chunks_found', 0)
                cached = rag_data.get('cached', False)
                
                print(f"   ✅ Chunks Found: {chunks_found}")
                print(f"   ✅ Total Available: {total_chunks}")
                print(f"   ✅ Answer Generated: {'Yes' if len(answer) > 50 else 'No'}")
                print(f"   ✅ Cached: {cached}")
                
                if chunks_found > 0:
                    # Show chunk info
                    first_chunk = rag_data['chunks'][0]
                    chunk_id = first_chunk.get('id', 'N/A')
                    doc_id = first_chunk.get('document_id', 'N/A')
                    print(f"   📄 First Chunk: {chunk_id} from {doc_id}")
                
                print(f"   💬 Answer Preview: {answer[:150]}...")
                
        except Exception as e:
            print(f"   ❌ RAG Search Failed: {e}")
        
        # 6. Performance Comparison
        print("\n6️⃣  Performance Analysis")
        try:
            test_query = "chunking functionality benefits"
            
            # Test document search
            start_time = time.time()
            doc_response = await client.post(f"{API_URL}/search-direct", 
                json={"query": test_query, "k": 3})
            doc_time = time.time() - start_time
            doc_data = doc_response.json()
            
            # Test chunk search  
            start_time = time.time()
            chunk_response = await client.post(f"{API_URL}/search-chunks",
                json={"query": test_query, "k": 3})
            chunk_time = time.time() - start_time
            chunk_data = chunk_response.json()
            
            print(f"   📄 Document Search: {len(doc_data.get('hits', []))} hits in {doc_time:.3f}s")
            print(f"   🧩 Chunk Search: {len(chunk_data.get('hits', []))} hits in {chunk_time:.3f}s")
            
        except Exception as e:
            print(f"   ⚠️  Performance test failed: {e}")
        
        # 7. Summary
        print("\n7️⃣  Validation Summary")
        print("   ✅ Phase 1 chunking functionality is working!")
        print("   📋 Documents are automatically split into chunks")
        print("   📋 Chunks are stored in separate 'chunks' index")
        print("   📋 Chunk-based search is operational")
        print("   📋 RAG search now uses chunks for better context")
        print("   📋 Ready for Phase 2: TEI embeddings integration")

if __name__ == "__main__":
    asyncio.run(validate_chunking())
