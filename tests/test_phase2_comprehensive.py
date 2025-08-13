#!/usr/bin/env python3
"""
Comprehensive Phase 2 (Embeddings Integration) Validation Test
Tests embedding generation, vector search, and RAG functionality
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:18000"

def test_embeddings_health():
    """Test that embeddings service is healthy"""
    print("\n=== Testing Embeddings Health ===")
    try:
        response = requests.get(f"{BASE_URL}/health")
        data = response.json()
        
        assert response.status_code == 200
        assert data["status"] == "healthy"
        assert data["embeddings_available"] == True
        assert data["embedding_dimensions"] == 384
        print("✅ Embeddings service is healthy")
        return True
    except Exception as e:
        print(f"❌ Embeddings health check failed: {e}")
        return False

def test_direct_embeddings():
    """Test direct embedding generation via test endpoint"""
    print("\n=== Testing Direct Embedding Generation ===")
    try:
        test_texts = ["semantic search test", "vector similarity matching"]
        response = requests.post(f"{BASE_URL}/test-embeddings", json=test_texts)
        data = response.json()
        
        assert response.status_code == 200
        assert data["input_count"] == 2
        assert data["embeddings_generated"] == 2
        assert data["dimensions"] == 384
        assert len(data["sample_embedding"]) == 5  # First 5 dimensions
        print("✅ Direct embedding generation working")
        return True
    except Exception as e:
        print(f"❌ Direct embedding test failed: {e}")
        return False

def test_document_ingestion_with_embeddings():
    """Test document ingestion with automatic embedding generation"""
    print("\n=== Testing Document Ingestion with Embeddings ===")
    try:
        documents = [
            {
                "id": f"phase2-validation-{int(time.time())}-1",
                "text": "Machine learning models require vector representations of text data. Embeddings provide dense numerical representations that capture semantic relationships between words and sentences.",
                "metadata": {"title": "ML Embeddings", "category": "machine-learning", "test": "phase2"}
            }
        ]
        
        response = requests.post(f"{BASE_URL}/ingest", json=documents)
        data = response.json()
        
        assert response.status_code == 200
        assert data["indexed"] == 1
        assert data["chunks_created"] == 1
        assert data["embeddings_generated"] == 1
        
        print("✅ Document ingestion with embeddings successful")
        time.sleep(2)  # Wait for indexing
        return True
    except Exception as e:
        print(f"❌ Document ingestion failed: {e}")
        return False

def test_semantic_search():
    """Test semantic search capabilities"""
    print("\n=== Testing Semantic Search ===")
    try:
        response = requests.post(f"{BASE_URL}/search", 
                               json={"query": "dense vector representations of text", "k": 3})
        data = response.json()
        
        assert response.status_code == 200
        assert "answer" in data
        assert "chunks" in data
        assert data["total_chunks_found"] > 0
        
        print("✅ Semantic search working")
        return True
    except Exception as e:
        print(f"❌ Semantic search failed: {e}")
        return False

def test_rag_with_embeddings():
    """Test RAG functionality with embedding-enhanced search"""
    print("\n=== Testing RAG with Embeddings ===")
    try:
        response = requests.post(f"{BASE_URL}/search", 
                               json={"query": "How do machine learning models represent text data?", "k": 3})
        data = response.json()
        
        assert response.status_code == 200
        assert "answer" in data
        assert len(data["answer"]) > 50  # Substantive answer
        assert "chunks" in data
        assert data["total_chunks_found"] > 0
        
        print("✅ RAG with embeddings working")
        return True
    except Exception as e:
        print(f"❌ RAG test failed: {e}")
        return False

def main():
    """Run comprehensive Phase 2 validation"""
    print("🚀 Phase 2 (Embeddings Integration) Comprehensive Validation")
    print("=" * 60)
    
    start_time = datetime.now()
    
    # Run all tests
    results = []
    results.append(("Embeddings Health", test_embeddings_health()))
    results.append(("Direct Embeddings", test_direct_embeddings()))
    results.append(("Document Ingestion", test_document_ingestion_with_embeddings()))
    results.append(("Semantic Search", test_semantic_search()))
    results.append(("RAG with Embeddings", test_rag_with_embeddings()))
    
    end_time = datetime.now()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 PHASE 2 VALIDATION SUMMARY")
    print("=" * 60)
    
    passed_tests = sum(1 for _, passed in results if passed)
    total_tests = len(results)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:20} {status}")
    
    success_rate = passed_tests / total_tests
    duration = (end_time - start_time).total_seconds()
    
    print(f"\nOverall Success Rate: {success_rate:.1%} ({passed_tests}/{total_tests})")
    print(f"Validation Duration: {duration:.1f} seconds")
    
    if success_rate >= 0.8:
        print("\n🎉 Phase 2 (Embeddings Integration) validation PASSED!")
    else:
        print("\n❌ Phase 2 validation needs attention")
    
    return success_rate >= 0.8

if __name__ == "__main__":
    main()
