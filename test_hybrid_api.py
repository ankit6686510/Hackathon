#!/usr/bin/env python3
"""
Test the hybrid search API endpoint
"""

import asyncio
import json
import requests
import time

def test_hybrid_search_api():
    """Test the hybrid search API endpoint"""
    
    print("🧪 Testing Hybrid Search API")
    print("=" * 40)
    
    base_url = "http://localhost:8000"
    
    # Test queries
    test_queries = [
        {
            "query": "merchant snapdeal (MID: snapdeal_test) is integrating the pinelabs_online gateway and are facing the INTERNAL_SERVER_ERROR in the /txns call",
            "description": "Your original problematic query"
        },
        {
            "query": "UPI payment failed with timeout",
            "description": "UPI payment issue"
        },
        {
            "query": "refund processing failed",
            "description": "Refund issue"
        },
        {
            "query": "webhook delivery not working",
            "description": "Webhook issue"
        },
        {
            "query": "database connection timeout",
            "description": "Non-payment query (should be rejected)"
        }
    ]
    
    for i, test_case in enumerate(test_queries, 1):
        print(f"\n🔍 Test {i}: {test_case['description']}")
        print(f"Query: '{test_case['query']}'")
        print("-" * 60)
        
        try:
            # Test hybrid search endpoint
            start_time = time.time()
            
            response = requests.post(
                f"{base_url}/api/v1/search/hybrid",
                json={
                    "query": test_case["query"],
                    "top_k": 3,
                    "search_type": "hybrid"
                },
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            execution_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                
                print(f"✅ Status: {response.status_code}")
                print(f"⏱️  Response Time: {execution_time:.0f}ms")
                print(f"📊 Results Found: {data['total_results']}")
                print(f"🔍 Search Type: {data['search_type']}")
                
                if data['results']:
                    print("\n📋 Top Results:")
                    for j, result in enumerate(data['results'][:3], 1):
                        print(f"  {j}. {result['id']} - {result['title'][:60]}...")
                        print(f"     Score: {result['score']:.3f}")
                        print(f"     Tags: {', '.join(result['tags'][:3])}")
                        if result.get('ai_suggestion'):
                            print(f"     AI Suggestion: {result['ai_suggestion'][:80]}...")
                        print()
                else:
                    print("❌ No results returned")
                    
            else:
                print(f"❌ Status: {response.status_code}")
                print(f"Error: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 Testing Complete!")
    
    # Test suggestions endpoint
    print("\n🔍 Testing Search Suggestions...")
    try:
        response = requests.get(f"{base_url}/api/v1/search/suggestions")
        if response.status_code == 200:
            suggestions = response.json()["suggestions"]
            print("✅ Suggestions available:")
            for suggestion in suggestions[:5]:
                print(f"  • {suggestion}")
        else:
            print(f"❌ Suggestions failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Suggestions error: {e}")

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

if __name__ == "__main__":
    # Check if backend is running
    if test_backend_health():
        print()
        test_hybrid_search_api()
    else:
        print("\n💡 Start the backend first, then run this test again.")
