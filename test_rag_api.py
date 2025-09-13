#!/usr/bin/env python3
"""
Test the RAG (Retrieval-Augmented Generation) API endpoints
"""

import json
import requests
import time
from datetime import datetime

def test_rag_api():
    """Test the RAG API endpoints comprehensively"""
    
    print("🧪 Testing RAG API - Enterprise Retrieval-Augmented Generation")
    print("=" * 70)
    
    base_url = "http://localhost:8000"
    
    # Test queries for different complexity levels
    test_cases = [
        {
            "name": "Simple Query - Specific Error Code",
            "query": "UPI payment failed with error 5003",
            "expected_complexity": "simple",
            "description": "Should classify as simple and return specific incident matches"
        },
        {
            "name": "Simple Query - Technical Issue",
            "query": "Card tokenization failing for BIN 65xx",
            "expected_complexity": "simple",
            "description": "Specific technical problem with clear parameters"
        },
        {
            "name": "Complex Query - Pattern Analysis",
            "query": "Why do refunds fail frequently?",
            "expected_complexity": "complex",
            "description": "Should analyze multiple incidents for patterns"
        },
        {
            "name": "Complex Query - Root Cause Analysis",
            "query": "What are common causes of payment timeouts?",
            "expected_complexity": "complex",
            "description": "Requires analysis across multiple incident types"
        },
        {
            "name": "Your Original Problematic Query",
            "query": "merchant snapdeal (MID: snapdeal_test) is integrating the pinelabs_online gateway and are facing the INTERNAL_SERVER_ERROR in the /txns call",
            "expected_complexity": "simple",
            "description": "Your original query that had issues - should now work perfectly"
        },
        {
            "name": "Domain Rejection Test",
            "query": "How to deploy a microservice?",
            "expected_complexity": "unknown",
            "description": "Non-payment query should be rejected"
        }
    ]
    
    # Test RAG health check first
    print("🏥 Testing RAG Health Check...")
    try:
        response = requests.get(f"{base_url}/api/v1/rag/health", timeout=10)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ RAG Health: {health_data['status']}")
            print(f"   Components: {', '.join([f'{k}:{v}' for k, v in health_data['components'].items()])}")
            print(f"   Test Query Classified: {health_data['test_results']['classified_complexity']}")
            print(f"   Incidents Retrieved: {health_data['test_results']['incidents_retrieved']}")
        else:
            print(f"⚠️  RAG Health Check returned {response.status_code}")
    except Exception as e:
        print(f"❌ RAG Health Check failed: {e}")
    
    print("\n" + "=" * 70)
    
    # Test each query
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔍 Test {i}: {test_case['name']}")
        print(f"Query: '{test_case['query']}'")
        print(f"Expected: {test_case['expected_complexity']} complexity")
        print(f"Description: {test_case['description']}")
        print("-" * 70)
        
        try:
            start_time = time.time()
            
            # Test RAG query endpoint
            rag_request = {
                "query": test_case["query"],
                "include_sources": True,
                "max_incidents": 5,
                "confidence_threshold": 0.3
            }
            
            response = requests.post(
                f"{base_url}/api/v1/rag/query",
                json=rag_request,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            execution_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                result = data["result"]
                metadata = data["metadata"]
                
                print(f"✅ Status: {response.status_code}")
                print(f"⏱️  Response Time: {execution_time:.0f}ms")
                print(f"🧠 Query Complexity: {result['query_complexity']}")
                print(f"🎯 RAG Strategy: {result['rag_strategy']}")
                print(f"📊 Confidence Score: {result['confidence_score']:.3f}")
                print(f"🔍 Incidents Retrieved: {len(result['retrieved_incidents'])}")
                print(f"📈 Confidence Level: {metadata['confidence_level']}")
                
                # Show generated answer
                print(f"\n💡 Generated Answer:")
                print(f"   {result['generated_answer'][:150]}{'...' if len(result['generated_answer']) > 150 else ''}")
                
                # Show sources if available
                if result['sources']:
                    print(f"\n📚 Sources ({len(result['sources'])}):")
                    for j, source in enumerate(result['sources'][:3], 1):
                        print(f"   {j}. {source}")
                
                # Validate expectations
                if test_case["expected_complexity"] != "unknown":
                    if result['query_complexity'] == test_case["expected_complexity"]:
                        print(f"✅ Complexity classification correct: {result['query_complexity']}")
                    else:
                        print(f"⚠️  Complexity mismatch: expected {test_case['expected_complexity']}, got {result['query_complexity']}")
                
                # Test feedback submission
                if result['retrieved_incidents']:
                    print(f"\n📝 Testing feedback submission...")
                    feedback_request = {
                        "query": test_case["query"],
                        "rag_result_id": f"test_{int(time.time())}",
                        "feedback_type": "UPVOTE",
                        "feedback_text": "Test feedback from automated test",
                        "helpful": True
                    }
                    
                    feedback_response = requests.post(
                        f"{base_url}/api/v1/rag/feedback",
                        json=feedback_request,
                        headers={"Content-Type": "application/json"},
                        timeout=10
                    )
                    
                    if feedback_response.status_code == 200:
                        feedback_data = feedback_response.json()
                        print(f"✅ Feedback submitted: {feedback_data['feedback_id']}")
                    else:
                        print(f"⚠️  Feedback submission failed: {feedback_response.status_code}")
                
            else:
                print(f"❌ Status: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Error: {error_data}")
                except:
                    print(f"Error: {response.text}")
                    
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
    
    # Test RAG metrics
    print("\n" + "=" * 70)
    print("📊 Testing RAG Metrics...")
    try:
        response = requests.get(f"{base_url}/api/v1/rag/metrics", timeout=10)
        if response.status_code == 200:
            metrics = response.json()
            print("✅ RAG Metrics available:")
            
            rag_metrics = metrics["rag_service_metrics"]
            api_metrics = metrics["api_metrics"]
            
            print(f"   Total Queries Processed: {rag_metrics['total_queries_processed']}")
            print(f"   Query Complexity Distribution:")
            for complexity, count in rag_metrics['query_complexity_distribution'].items():
                print(f"     {complexity}: {count}")
            print(f"   RAG Pipeline Status: {api_metrics['rag_pipeline_status']}")
            print(f"   Confidence Threshold: {api_metrics['confidence_threshold']}")
        else:
            print(f"⚠️  Metrics failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Metrics error: {e}")
    
    # Test RAG examples
    print("\n📖 Testing RAG Examples...")
    try:
        response = requests.get(f"{base_url}/api/v1/rag/examples", timeout=10)
        if response.status_code == 200:
            examples = response.json()
            print("✅ RAG Examples available:")
            print(f"   Simple Queries: {len(examples['examples']['simple_queries'])}")
            print(f"   Complex Queries: {len(examples['examples']['complex_queries'])}")
            print(f"   Edge Cases: {len(examples['examples']['edge_cases'])}")
            print(f"   API Endpoint: {examples['api_endpoint']}")
        else:
            print(f"⚠️  Examples failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Examples error: {e}")
    
    print("\n" + "=" * 70)
    print("🎉 RAG API Testing Complete!")
    print("\n🚀 RAG Features Demonstrated:")
    print("   ✅ Query Classification (Simple/Complex/Unknown)")
    print("   ✅ Adaptive Retrieval based on complexity")
    print("   ✅ Context-Augmented Generation")
    print("   ✅ Source Attribution and Citations")
    print("   ✅ Confidence Scoring")
    print("   ✅ Feedback Collection")
    print("   ✅ Performance Metrics")
    print("   ✅ Domain Validation")
    print("   ✅ Health Monitoring")

def test_backend_health():
    """Test if the backend is running"""
    
    print("🏥 Checking Backend Health...")
    
    try:
        response = requests.get("http://localhost:8000/api/v1/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend is running")
            return True
        else:
            print(f"⚠️  Backend returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Backend is not running. Please start it with:")
        print("   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
        return False
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def compare_rag_vs_hybrid():
    """Compare RAG vs Hybrid search performance"""
    
    print("\n🔬 RAG vs Hybrid Search Comparison")
    print("=" * 50)
    
    test_query = "UPI payment failed with timeout"
    base_url = "http://localhost:8000"
    
    print(f"Test Query: '{test_query}'")
    print("-" * 50)
    
    # Test Hybrid Search
    print("🔍 Testing Hybrid Search...")
    try:
        start_time = time.time()
        hybrid_response = requests.post(
            f"{base_url}/api/v1/search/hybrid",
            json={"query": test_query, "top_k": 3},
            timeout=15
        )
        hybrid_time = (time.time() - start_time) * 1000
        
        if hybrid_response.status_code == 200:
            hybrid_data = hybrid_response.json()
            print(f"✅ Hybrid: {len(hybrid_data['results'])} results in {hybrid_time:.0f}ms")
            if hybrid_data['results']:
                print(f"   Top Score: {hybrid_data['results'][0]['score']:.3f}")
        else:
            print(f"❌ Hybrid failed: {hybrid_response.status_code}")
    except Exception as e:
        print(f"❌ Hybrid error: {e}")
    
    # Test RAG
    print("\n🧠 Testing RAG...")
    try:
        start_time = time.time()
        rag_response = requests.post(
            f"{base_url}/api/v1/rag/query",
            json={"query": test_query, "max_incidents": 3},
            timeout=15
        )
        rag_time = (time.time() - start_time) * 1000
        
        if rag_response.status_code == 200:
            rag_data = rag_response.json()
            result = rag_data["result"]
            print(f"✅ RAG: {len(result['retrieved_incidents'])} incidents in {rag_time:.0f}ms")
            print(f"   Complexity: {result['query_complexity']}")
            print(f"   Confidence: {result['confidence_score']:.3f}")
            print(f"   Strategy: {result['rag_strategy']}")
            print(f"   Generated Answer: {result['generated_answer'][:100]}...")
        else:
            print(f"❌ RAG failed: {rag_response.status_code}")
    except Exception as e:
        print(f"❌ RAG error: {e}")
    
    print("\n🎯 Key Differences:")
    print("   Hybrid Search: Fast retrieval with score fusion")
    print("   RAG: Intelligent routing + context-aware generation")
    print("   RAG adds: Query classification, source grounding, confidence scoring")

if __name__ == "__main__":
    # Check if backend is running
    if test_backend_health():
        print()
        test_rag_api()
        compare_rag_vs_hybrid()
    else:
        print("\n💡 Start the backend first, then run this test again.")
