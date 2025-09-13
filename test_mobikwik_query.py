#!/usr/bin/env python3
"""
Test the MobiKwik query with improved "no results" handling
"""

import requests
import json
import time

def test_mobikwik_query():
    """Test the specific MobiKwik query that was returning irrelevant results"""
    
    print("🧪 Testing MobiKwik Query - Improved 'No Results' Handling")
    print("=" * 70)
    
    base_url = "http://localhost:8000"
    
    # Your original problematic query
    mobikwik_query = """We are currently observing a 0% Success Rate for Mobikwik Wallet transactions through PayU PG for MID: citymall. All transactions are failing with the error message: "Invalid data received from bank."
As per the update from the MobiKwik bank team (via PayU), it appears that two different integration flows are active under the same MID. However, the Power Wallet flow is being triggered instead of the expected Redirection flow, which could be leading to these failures.
Requesting your help to check and confirm which API or flow is currently being invoked from our side so we can take appropriate action."""
    
    print(f"🔍 Testing Query:")
    print(f"'{mobikwik_query[:100]}...'")
    print("-" * 70)
    
    # Test with RAG endpoint (improved handling)
    print("\n🧠 Testing with RAG Endpoint (Improved)...")
    try:
        start_time = time.time()
        
        rag_response = requests.post(
            f"{base_url}/api/v1/rag/query",
            json={
                "query": mobikwik_query,
                "include_sources": True,
                "max_incidents": 5
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        rag_time = (time.time() - start_time) * 1000
        
        if rag_response.status_code == 200:
            data = rag_response.json()
            result = data["result"]
            metadata = data["metadata"]
            
            print(f"✅ Status: {rag_response.status_code}")
            print(f"⏱️  Response Time: {rag_time:.0f}ms")
            print(f"🧠 Query Complexity: {result['query_complexity']}")
            print(f"🎯 RAG Strategy: {result['rag_strategy']}")
            print(f"📊 Confidence Score: {result['confidence_score']:.3f}")
            print(f"🔍 Incidents Retrieved: {len(result['retrieved_incidents'])}")
            
            print(f"\n💡 Generated Answer:")
            print("=" * 50)
            print(result['generated_answer'])
            print("=" * 50)
            
            if result['sources']:
                print(f"\n📚 Sources ({len(result['sources'])}):")
                for i, source in enumerate(result['sources'], 1):
                    print(f"   {i}. {source}")
            else:
                print("\n📚 No sources (as expected for irrelevant matches)")
                
        else:
            print(f"❌ RAG failed: {rag_response.status_code}")
            print(f"Error: {rag_response.text}")
            
    except Exception as e:
        print(f"❌ RAG error: {e}")
    
    # Compare with Hybrid Search (old behavior)
    print("\n🔍 Testing with Hybrid Search (Old Behavior)...")
    try:
        start_time = time.time()
        
        hybrid_response = requests.post(
            f"{base_url}/api/v1/search/hybrid",
            json={
                "query": mobikwik_query,
                "top_k": 3
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        hybrid_time = (time.time() - start_time) * 1000
        
        if hybrid_response.status_code == 200:
            data = hybrid_response.json()
            
            print(f"✅ Status: {hybrid_response.status_code}")
            print(f"⏱️  Response Time: {hybrid_time:.0f}ms")
            print(f"📊 Results Found: {data['total_results']}")
            
            if data['results']:
                print(f"\n📋 Top Result (Potentially Irrelevant):")
                top_result = data['results'][0]
                print(f"   ID: {top_result['id']}")
                print(f"   Title: {top_result['title']}")
                print(f"   Score: {top_result['score']:.3f}")
                print(f"   Tags: {', '.join(top_result['tags'][:3])}")
                
                # Check if this is actually relevant
                title_lower = top_result['title'].lower()
                query_lower = mobikwik_query.lower()
                
                has_mobikwik = 'mobikwik' in title_lower or 'mobikwik' in query_lower
                has_payu = 'payu' in title_lower or 'payu' in query_lower
                has_wallet = 'wallet' in title_lower or 'wallet' in query_lower
                
                if not (has_mobikwik or has_payu or has_wallet):
                    print(f"   ⚠️  IRRELEVANT: No MobiKwik/PayU/Wallet terms in result!")
                else:
                    print(f"   ✅ Potentially relevant")
            else:
                print("\n❌ No results from hybrid search")
                
        else:
            print(f"❌ Hybrid failed: {hybrid_response.status_code}")
            
    except Exception as e:
        print(f"❌ Hybrid error: {e}")
    
    print("\n" + "=" * 70)
    print("🎯 Expected Behavior:")
    print("✅ RAG should return 'No Relevant Historical Incidents Found'")
    print("✅ Should provide helpful next steps and keywords")
    print("✅ Should NOT force irrelevant matches")
    print("⚠️  Hybrid search might still return irrelevant results (old behavior)")

def test_other_queries():
    """Test a few other queries to ensure the system still works for good matches"""
    
    print("\n🧪 Testing Other Queries (Should Still Work)")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    
    test_queries = [
        {
            "query": "UPI payment failed with error 5003",
            "should_find_results": True,
            "description": "Should find relevant UPI incidents"
        },
        {
            "query": "How to configure Kubernetes deployment",
            "should_find_results": False,
            "description": "Non-payment query - should be rejected"
        }
    ]
    
    for i, test_case in enumerate(test_queries, 1):
        print(f"\n🔍 Test {i}: {test_case['description']}")
        print(f"Query: '{test_case['query']}'")
        print("-" * 40)
        
        try:
            response = requests.post(
                f"{base_url}/api/v1/rag/query",
                json={"query": test_case["query"]},
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                result = data["result"]
                
                has_incidents = len(result['retrieved_incidents']) > 0
                strategy = result['rag_strategy']
                
                print(f"✅ Strategy: {strategy}")
                print(f"📊 Incidents: {len(result['retrieved_incidents'])}")
                
                if test_case["should_find_results"]:
                    if has_incidents:
                        print("✅ Correctly found relevant results")
                    else:
                        print("⚠️  Expected results but got none")
                else:
                    if not has_incidents:
                        print("✅ Correctly returned no results")
                    else:
                        print("⚠️  Expected no results but got some")
                        
            else:
                print(f"❌ Failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error: {e}")

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
    if test_backend_health():
        print()
        test_mobikwik_query()
        test_other_queries()
        print("\n🎉 Testing Complete!")
        print("\nThe improved RAG system should now:")
        print("✅ Honestly say 'no results' for irrelevant queries")
        print("✅ Provide helpful next steps and keywords")
        print("✅ Maintain trust by not forcing poor matches")
    else:
        print("\n💡 Start the backend first, then run this test again.")
