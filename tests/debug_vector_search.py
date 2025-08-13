#!/usr/bin/env python3
"""Debug vector search issues"""

import requests
import json

def main():
    print("🔍 Debugging vector search format issues...")
    
    # Test 1: Check health endpoint
    print("\n1. Testing health endpoint format...")
    response = requests.get("http://localhost:18000/health")
    print(f"Health Response: {response.json()}")
    
    # Test 2: Test direct embedding generation
    print("\n2. Testing direct embedding generation...")
    response = requests.post("http://localhost:18000/test-embeddings", 
                            json=["test vector search format"])
    data = response.json()
    print(f"Embedding format: {type(data['sample_embedding'])}")
    print(f"First few values: {data['sample_embedding'][:3]}")
    
    # Test 3: Attempt vector search with detailed response
    print("\n3. Testing vector search (expecting fallback to text)...")
    response = requests.post("http://localhost:18000/search", 
                            json={"query": "vector embeddings test", "k": 1})
    data = response.json()
    print(f"Search method used: {data['search_method']}")
    print(f"Found chunks: {data['total_chunks_found']}")
    
    return True

if __name__ == "__main__":
    main()
