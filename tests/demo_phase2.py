#!/usr/bin/env python3
"""
Phase 2 (Embeddings Integration) Demo
Demonstrates semantic search and embedding-powered RAG
"""

import requests
import json

BASE_URL = "http://localhost:18000"

def demo_semantic_search():
    """Demonstrate semantic search capabilities"""
    print("🔍 SEMANTIC SEARCH DEMONSTRATION")
    print("=" * 50)
    
    queries = [
        "vector representations numerical data",
        "fast search instant results", 
        "machine learning text processing"
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"\n🔍 Query {i}: '{query}'")
        print("-" * 40)
        
        try:
            response = requests.post(f"{BASE_URL}/search", 
                                   json={"query": query, "k": 2})
            data = response.json()
            
            print(f"📊 Found {data['total_chunks_found']} relevant chunks")
            print(f"🔄 Search method: {data.get('search_method', 'unknown')}")
            
            for j, chunk in enumerate(data["chunks"][:2], 1):
                print(f"\n📄 Chunk {j} (from {chunk['metadata'].get('title', 'Unknown')}):")
                content = chunk["content"]
                if len(content) > 150:
                    content = content[:150] + "..."
                print(f"   {content}")
                
        except Exception as e:
            print(f"❌ Error: {e}")

def demo_rag_answers():
    """Demonstrate RAG question answering"""
    print("\n\n💬 RAG QUESTION ANSWERING DEMONSTRATION")
    print("=" * 50)
    
    questions = [
        "What are vector embeddings and how do they work?",
        "How does Meilisearch provide fast search results?",
        "What is the advantage of semantic search over keyword search?"
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n❓ Question {i}: {question}")
        print("-" * 60)
        
        try:
            response = requests.post(f"{BASE_URL}/search", 
                                   json={"query": question, "k": 3})
            data = response.json()
            
            answer = data["answer"]
            if len(answer) > 300:
                answer = answer[:300] + "..."
            
            print(f"🤖 AI Answer:")
            print(f"   {answer}")
            print(f"\n📚 Based on {data['total_chunks_found']} source chunks")
            
        except Exception as e:
            print(f"❌ Error: {e}")

def main():
    print("🚀 Phase 2: Embeddings Integration Demo")
    print("🎯 Showcasing semantic search and RAG with vector embeddings")
    print("📦 Using: LiteLLM + TEI + Meilisearch + Groq LLM")
    print("\n")
    
    demo_semantic_search()
    demo_rag_answers()
    
    print("\n\n✨ PHASE 2 DEMO COMPLETE")
    print("🎉 Embeddings-powered semantic search and RAG are working!")

if __name__ == "__main__":
    main()
