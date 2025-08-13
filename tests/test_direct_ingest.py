#!/usr/bin/env python3
"""
Test direct ingestion to Meilisearch with and without embeddings
"""
import asyncio
import httpx

async def test_direct_meilisearch():
    """Test adding documents directly to Meilisearch"""
    
    # Test 1: Add document without embeddings (should fail)
    print("🧪 Test 1: Adding document without embeddings...")
    doc_without_embeddings = [{
        "id": "test-1", 
        "content": "This is a test document without embeddings"
    }]
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:7700/indexes/documents/documents",
            headers={"Authorization": "Bearer change_me_master_key"},
            json=doc_without_embeddings
        )
        print(f"   Response: {response.status_code}")
        if response.status_code != 202:
            print(f"   Error: {response.text}")
    
    # Test 2: Add document with embeddings (should work)
    print("\n🧪 Test 2: Adding document with embeddings...")
    doc_with_embeddings = [{
        "id": "test-2",
        "content": "This is a test document with embeddings",
        "_vectors": {
            "default": [0.1] * 384  # 384-dimensional zero vector
        }
    }]
    
    response = await client.post(
        "http://localhost:7700/indexes/documents/documents", 
        headers={"Authorization": "Bearer change_me_master_key"},
        json=doc_with_embeddings
    )
    print(f"   Response: {response.status_code}")
    if response.status_code == 202:
        print("   ✅ Success! Document with embeddings accepted")
    else:
        print(f"   Error: {response.text}")
    
    # Test 3: Check if documents are now visible
    await asyncio.sleep(2)  # Wait for indexing
    print("\n🔍 Checking documents in index...")
    
    response = await client.get(
        "http://localhost:7700/indexes/documents/documents",
        headers={"Authorization": "Bearer change_me_master_key"}
    )
    result = response.json()
    print(f"   Total documents: {result['total']}")
    for doc in result.get('results', []):
        print(f"   - {doc['id']}: {doc['content']}")

if __name__ == "__main__":
    asyncio.run(test_direct_meilisearch())
