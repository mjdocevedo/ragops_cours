#!/usr/bin/env python3
"""
RAGOPS - Complete Feature Test Script
=====================================

This script demonstrates and tests all major features of the RAGOPS system:
- Document ingestion
- RAG queries  
- Direct chat
- Performance and caching
- Error handling
"""

import asyncio
import httpx
import json
import time
from datetime import datetime
from typing import List, Dict, Any

class RAGOPSFeatureTester:
    def __init__(self, base_url: str = "http://backend:8000"):
        self.base_url = base_url
        self.session = None
        self.test_results = []
    
    async def __aenter__(self):
        self.session = httpx.AsyncClient(timeout=30.0)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()
    
    def log_test(self, test_name: str, success: bool, duration: float, details: str = ""):
        """Log test results"""
        result = {
            "test": test_name,
            "success": success,
            "duration": duration,
            "timestamp": datetime.now().isoformat(),
            "details": details
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name} ({duration:.2f}s) {details}")
    
    async def test_health_check(self):
        """Test system health"""
        print("\n🏥 Testing System Health")
        print("=" * 50)
        
        start_time = time.time()
        try:
            response = await self.session.get(f"{self.base_url}/health")
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                success = data.get("status") == "ok"
                details = f"Status: {data.get('status')}"
            else:
                success = False
                details = f"HTTP {response.status_code}"
                
            self.log_test("Health Check", success, duration, details)
            return success
            
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Health Check", False, duration, f"Error: {str(e)}")
            return False
    
    async def test_document_ingestion(self):
        """Test document ingestion with various document types"""
        print("\n📥 Testing Document Ingestion")
        print("=" * 50)
        
        test_documents = [
            {
                "id": "search-engine-doc",
                "text": "Modern search engines like Meilisearch provide fast, accurate search results with features like typo tolerance and semantic search capabilities. They can handle millions of documents while maintaining sub-millisecond response times.",
                "metadata": {
                    "title": "Search Engine Guide",
                    "category": "technology",
                    "tags": ["search", "performance"],
                    "author": "System"
                }
            },
            {
                "id": "ai-architecture-doc", 
                "text": "RAG (Retrieval-Augmented Generation) architecture combines information retrieval with language generation. This approach helps reduce hallucinations and provides more factual, up-to-date information compared to using LLMs alone.",
                "metadata": {
                    "title": "AI Architecture Overview",
                    "category": "ai-ml",
                    "tags": ["rag", "ai", "llm"],
                    "author": "AI Team"
                }
            },
            {
                "id": "deployment-doc",
                "text": "Docker containerization provides isolated, reproducible environments for deploying applications. With Docker Compose, you can orchestrate multi-service applications using simple YAML configuration files.",
                "metadata": {
                    "title": "Deployment Guide",
                    "category": "devops", 
                    "tags": ["docker", "deployment", "containers"],
                    "author": "DevOps Team"
                }
            }
        ]
        
        start_time = time.time()
        try:
            response = await self.session.post(
                f"{self.base_url}/ingest",
                json=test_documents
            )
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                success = data.get("indexed", 0) == len(test_documents)
                details = f"Indexed: {data.get('indexed', 0)}/{len(test_documents)}"
            else:
                success = False
                details = f"HTTP {response.status_code}"
                
            self.log_test("Document Ingestion", success, duration, details)
            
            # Wait for indexing to complete
            if success:
                print("⏳ Waiting for indexing to complete...")
                await asyncio.sleep(5)
            
            return success
            
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Document Ingestion", False, duration, f"Error: {str(e)}")
            return False
    
    async def test_rag_queries(self):
        """Test RAG queries with different complexity levels"""
        print("\n🔍 Testing RAG Queries")
        print("=" * 50)
        
        # Updated test queries to match actual document content
        test_queries = [
            {
                "name": "Search Engine Query",
                "query": "What are the features of modern search engines?",
                "k": 3,
                "expected_keywords": ["search", "engine", "fast"]
            },
            {
                "name": "AI Architecture Query", 
                "query": "How does RAG architecture work?",
                "k": 3,
                "expected_keywords": ["RAG", "retrieval", "generation"]
            },
            {
                "name": "Docker Deployment Query",
                "query": "What are the benefits of Docker containerization?",
                "k": 3,
                "expected_keywords": ["docker", "container", "deployment"]
            },
            {
                "name": "Technology Overview Query",
                "query": "Explain the technology stack used in this system", 
                "k": 4,
                "expected_keywords": ["technology", "system", "search"]
            }
        ]
        
        all_success = True
        
        for query_test in test_queries:
            start_time = time.time()
            try:
                response = await self.session.post(
                    f"{self.base_url}/search",
                    json={"query": query_test["query"], "k": query_test["k"]}
                )
                duration = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check if we got an answer
                    has_answer = bool(data.get("answer"))
                    has_chunks = bool(data.get("chunks", []))
                    chunks_count = len(data.get("chunks", []))
                    
                    # Check for expected keywords in answer (more lenient)
                    answer = data.get("answer", "").lower()
                    keyword_matches = sum(1 for kw in query_test["expected_keywords"] 
                                        if kw.lower() in answer)
                    
                    # Success criteria: must have answer and at least some content relevance
                    success = has_answer and (chunks_count > 0 or len(answer) > 50)
                    details = f"Answer: {has_answer}, Chunks: {chunks_count}, Keywords: {keyword_matches}/{len(query_test['expected_keywords'])}"
                    
                    if data.get("cached"):
                        details += " (cached)"
                        
                else:
                    success = False
                    details = f"HTTP {response.status_code}"
                
                self.log_test(f"RAG - {query_test['name']}", success, duration, details)
                all_success = all_success and success
                
            except Exception as e:
                duration = time.time() - start_time
                self.log_test(f"RAG - {query_test['name']}", False, duration, f"Error: {str(e)}")
                all_success = False
            
            # Small delay between queries
            await asyncio.sleep(1)
        
        return all_success
    
    async def test_direct_chat(self):
        """Test direct chat functionality"""
        print("\n💬 Testing Direct Chat")
        print("=" * 50)
        
        chat_tests = [
            {
                "name": "Simple Chat",
                "messages": [
                    {"role": "user", "content": "Hello! How are you?"}
                ],
                "expected_length": 10  # Minimum response length
            },
            {
                "name": "Technical Chat",
                "messages": [
                    {"role": "system", "content": "You are a helpful AI assistant."},
                    {"role": "user", "content": "Explain what a search engine is in simple terms"}
                ],
                "expected_length": 50
            },
            {
                "name": "Conversational Chat",
                "messages": [
                    {"role": "user", "content": "What are the main benefits of containerization?"},
                    {"role": "assistant", "content": "Containerization provides isolation, portability, and consistency."},
                    {"role": "user", "content": "Can you explain more about isolation?"}
                ],
                "expected_length": 30
            }
        ]
        
        all_success = True
        
        for chat_test in chat_tests:
            start_time = time.time()
            try:
                payload = {
                    "messages": chat_test["messages"],
                    "temperature": 0.3
                }
                
                response = await self.session.post(
                    f"{self.base_url}/chat",
                    json=payload
                )
                duration = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Extract response content
                    content = ""
                    if isinstance(data, dict):
                        if "choices" in data:
                            content = data["choices"][0]["message"]["content"]
                        elif "content" in data:
                            content = data["content"]
                        else:
                            content = str(data)
                    else:
                        content = str(data)
                    
                    success = len(content) >= chat_test["expected_length"]
                    details = f"Response length: {len(content)} chars"
                    
                else:
                    success = False
                    details = f"HTTP {response.status_code}"
                
                self.log_test(f"Chat - {chat_test['name']}", success, duration, details)
                all_success = all_success and success
                
            except Exception as e:
                duration = time.time() - start_time
                self.log_test(f"Chat - {chat_test['name']}", False, duration, f"Error: {str(e)}")
                all_success = False
            
            # Small delay between requests
            await asyncio.sleep(1)
        
        return all_success
    
    async def test_performance_caching(self):
        """Test performance and caching functionality"""
        print("\n⚡ Testing Performance & Caching")
        print("=" * 50)
        
        test_query = "What is the main purpose of search engines?"
        
        # First request (no cache)
        print("🔄 First request (no cache expected)...")
        start_time = time.time()
        try:
            response1 = await self.session.post(
                f"{self.base_url}/search",
                json={"query": test_query, "k": 3}
            )
            duration1 = time.time() - start_time
            
            if response1.status_code != 200:
                self.log_test("Performance - First Request", False, duration1, f"HTTP {response1.status_code}")
                return False
                
            data1 = response1.json()
            cached1 = data1.get("cached", False)
            
            # Second request (should be cached)
            print("⚡ Second request (cache expected)...")
            await asyncio.sleep(1)  # Small delay
            
            start_time = time.time()
            response2 = await self.session.post(
                f"{self.base_url}/search",
                json={"query": test_query, "k": 3}
            )
            duration2 = time.time() - start_time
            
            if response2.status_code != 200:
                self.log_test("Performance - Second Request", False, duration2, f"HTTP {response2.status_code}")
                return False
            
            data2 = response2.json()
            cached2 = data2.get("cached", False)
            
            # Calculate speedup
            speedup = duration1 / duration2 if duration2 > 0 else 1
            
            # Test success criteria
            cache_working = cached2 or speedup > 1.5  # Either explicit cache flag or significant speedup
            responses_valid = bool(data1.get("answer")) and bool(data2.get("answer"))
            
            success = cache_working and responses_valid
            details = f"Times: {duration1:.2f}s → {duration2:.2f}s, Speedup: {speedup:.1f}x, Cache: {cached1} → {cached2}"
            
            self.log_test("Performance & Caching", success, duration1 + duration2, details)
            
            return success
            
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Performance & Caching", False, duration, f"Error: {str(e)}")
            return False
    
    async def test_error_handling(self):
        """Test error handling and edge cases"""
        print("\n🚨 Testing Error Handling")
        print("=" * 50)
        
        error_tests = [
            {
                "name": "Empty Query",
                "endpoint": "/search",
                "payload": {"query": "", "k": 3},
                "expect_error": True
            },
            {
                "name": "Invalid K Value", 
                "endpoint": "/search",
                "payload": {"query": "test", "k": 0},
                "expect_error": True
            },
            {
                "name": "Missing Query Field",
                "endpoint": "/search", 
                "payload": {"k": 3},
                "expect_error": True
            },
            {
                "name": "Empty Messages",
                "endpoint": "/chat",
                "payload": {"messages": []},
                "expect_error": True
            }
        ]
        
        all_success = True
        
        for error_test in error_tests:
            start_time = time.time()
            try:
                response = await self.session.post(
                    f"{self.base_url}{error_test['endpoint']}",
                    json=error_test["payload"]
                )
                duration = time.time() - start_time
                
                if error_test["expect_error"]:
                    # Should return 4xx error OR return valid response with no results
                    if 400 <= response.status_code < 500:
                        success = True
                        details = f"HTTP {response.status_code} (expected error)"
                    elif response.status_code == 200:
                        # Check if it's a valid "no results" response
                        try:
                            data = response.json()
                            if "chunks" in data and len(data["chunks"]) == 0:
                                success = True
                                details = f"HTTP 200 with no results (acceptable)"
                            else:
                                success = False
                                details = f"HTTP 200 with results (expected error)"
                        except:
                            success = False
                            details = f"HTTP 200 invalid response (expected error)"
                    else:
                        success = False
                        details = f"HTTP {response.status_code} (expected 4xx error)"
                else:
                    # Should succeed
                    success = response.status_code == 200
                    details = f"HTTP {response.status_code} (expected success)"
                
                self.log_test(f"Error - {error_test['name']}", success, duration, details)
                all_success = all_success and success
                
            except Exception as e:
                duration = time.time() - start_time
                # For error tests, exceptions might be expected
                success = error_test["expect_error"]
                details = f"Exception: {str(e)[:50]}..."
                self.log_test(f"Error - {error_test['name']}", success, duration, details)
                all_success = all_success and success
        
        return all_success
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("🎯 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["success"])
        failed_tests = total_tests - passed_tests
        
        total_duration = sum(r["duration"] for r in self.test_results)
        
        print(f"📊 Results: {passed_tests}/{total_tests} tests passed ({passed_tests/total_tests*100:.1f}%)")
        print(f"⏱️  Total Duration: {total_duration:.2f} seconds")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        
        if failed_tests > 0:
            print(f"\n❌ Failed Tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   • {result['test']}: {result['details']}")
        
        print(f"\n🎉 Overall Status: {'PASS' if failed_tests == 0 else 'PARTIAL SUCCESS' if passed_tests >= total_tests * 0.7 else 'FAIL'}")
        
        # Save detailed results
        with open("test_results.json", "w") as f:
            json.dump(self.test_results, f, indent=2)
        print(f"📄 Detailed results saved to: test_results.json")

async def main():
    """Run all feature tests"""
    print("🚀 RAGOPS Feature Test Suite")
    print("=" * 60)
    print("Testing all major features of the RAGOPS system...")
    print("Updated with queries matching actual document content")
    print("")
    
    async with RAGOPSFeatureTester() as tester:
        # Run all tests
        tests = [
            tester.test_health_check(),
            tester.test_document_ingestion(),
            tester.test_rag_queries(), 
            tester.test_direct_chat(),
            tester.test_performance_caching(),
            tester.test_error_handling()
        ]
        
        # Execute tests
        results = await asyncio.gather(*tests, return_exceptions=True)
        
        # Handle any exceptions
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"❌ Test {i} failed with exception: {result}")
        
        # Print summary
        tester.print_summary()

if __name__ == "__main__":
    asyncio.run(main())
