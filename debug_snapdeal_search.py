#!/usr/bin/env python3
"""
Debug why Snapdeal + Pinelabs query is not finding JSP-1052
"""

import requests
import json
import time

def test_snapdeal_search():
    """Test different search methods for Snapdeal query"""
    
    print("🔍 Debugging Snapdeal + Pinelabs Search Issue")
    print("=" * 60)
    
    base_url = "http://localhost:8000"
    
    # Your exact query
    snapdeal_query = "merchant snapdeal (MID: snapdeal_test) is integrating the pinelabs_online gateway and are facing the INTERNAL_SERVER_ERROR in the /txns call"
    
    print(f"🎯 Target Result: JSP-1052 - Pinelabs Online Gateway RSA Decryption Failure")
    print(f"📝 Query: '{snapdeal_query}'")
    print("-" * 60)
    
    # Test 1: RAG Search
    print("\n🧠 Testing RAG Search...")
    try:
        response = requests.post(
            f"{base_url}/api/v1/rag/query",
            json={"query": snapdeal_query},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            result = data["result"]
            
            print(f"✅ Status: {response.status_code}")
            print(f"🎯 Strategy: {result['rag_strategy']}")
            print(f"📊 Confidence: {result['confidence_score']:.3f}")
            print(f"🔍 Incidents: {len(result['retrieved_incidents'])}")
            
            if result['retrieved_incidents']:
                print(f"\n📋 Retrieved Incidents:")
                for i, incident in enumerate(result['retrieved_incidents'], 1):
                    print(f"   {i}. {incident.get('id', 'Unknown')} - {incident.get('title', 'No title')[:50]}...")
                    print(f"      Score: {incident.get('fused_score', incident.get('score', 0)):.3f}")
                    print(f"      Tags: {incident.get('tags', [])}")
                    
                    # Check if JSP-1052 is found
                    if incident.get('id') == 'JSP-1052':
                        print(f"      ✅ FOUND TARGET INCIDENT!")
                    else:
                        print(f"      ❌ Not the target incident")
            else:
                print("❌ No incidents retrieved")
        else:
            print(f"❌ RAG failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ RAG error: {e}")
    
    # Test 2: Hybrid Search
    print("\n🔍 Testing Hybrid Search...")
    try:
        response = requests.post(
            f"{base_url}/api/v1/search/hybrid",
            json={"query": snapdeal_query, "top_k": 5},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"✅ Status: {response.status_code}")
            print(f"📊 Results: {data['total_results']}")
            
            if data['results']:
                print(f"\n📋 Hybrid Search Results:")
                for i, result in enumerate(data['results'], 1):
                    print(f"   {i}. {result['id']} - {result['title'][:50]}...")
                    print(f"      Score: {result['score']:.3f}")
                    print(f"      Tags: {result['tags']}")
                    
                    # Check if JSP-1052 is found
                    if result['id'] == 'JSP-1052':
                        print(f"      ✅ FOUND TARGET INCIDENT!")
                    else:
                        print(f"      ❌ Not the target incident")
            else:
                print("❌ No results from hybrid search")
        else:
            print(f"❌ Hybrid failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Hybrid error: {e}")
    
    # Test 3: Simple keyword search
    print("\n🔑 Testing Simple Keyword Searches...")
    
    keyword_tests = [
        "snapdeal",
        "pinelabs",
        "JSP-1052",
        "snapdeal pinelabs",
        "INTERNAL_SERVER_ERROR",
        "snapdeal_test"
    ]
    
    for keyword in keyword_tests:
        print(f"\n   Testing keyword: '{keyword}'")
        try:
            response = requests.post(
                f"{base_url}/api/v1/search/hybrid",
                json={"query": keyword, "top_k": 3},
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                found_target = False
                
                for result in data['results']:
                    if result['id'] == 'JSP-1052':
                        found_target = True
                        print(f"      ✅ Found JSP-1052 with score {result['score']:.3f}")
                        break
                
                if not found_target:
                    print(f"      ❌ JSP-1052 not in top 3 results")
                    if data['results']:
                        print(f"      Top result: {data['results'][0]['id']} (score: {data['results'][0]['score']:.3f})")
            else:
                print(f"      ❌ Search failed: {response.status_code}")
                
        except Exception as e:
            print(f"      ❌ Error: {e}")

def check_search_indices():
    """Check if search indices are properly built"""
    
    print("\n🔧 Checking Search Index Status...")
    print("-" * 40)
    
    base_url = "http://localhost:8000"
    
    try:
        # Check hybrid search stats
        response = requests.get(f"{base_url}/api/v1/rag/metrics", timeout=10)
        if response.status_code == 200:
            metrics = response.json()
            print("✅ RAG metrics available")
        else:
            print(f"⚠️  RAG metrics failed: {response.status_code}")
    except Exception as e:
        print(f"❌ RAG metrics error: {e}")

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
        print("❌ Backend is not running")
        return False
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

if __name__ == "__main__":
    if test_backend_health():
        print()
        test_snapdeal_search()
        check_search_indices()
        
        print("\n" + "=" * 60)
        print("🎯 Expected Behavior:")
        print("✅ JSP-1052 should be the TOP result for Snapdeal + Pinelabs query")
        print("✅ Should have high relevance score (>0.8)")
        print("✅ Should match on: snapdeal, pinelabs_online, INTERNAL_SERVER_ERROR")
        print("❌ Currently returning irrelevant FirstCry result instead")
        
        print("\n💡 Possible Issues:")
        print("1. Search indices not properly built/updated")
        print("2. BM25/TF-IDF not finding keyword matches")
        print("3. Semantic search not understanding context")
        print("4. Score fusion algorithm issues")
        print("5. Confidence thresholds too strict")
    else:
        print("\n💡 Start the backend first, then run this test again.")
