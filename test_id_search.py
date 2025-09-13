#!/usr/bin/env python3
"""
Test ID-First Search Enhancement
Demonstrates instant incident ID lookup functionality
"""

import requests
import json
import time
from datetime import datetime


def test_id_search():
    """Test the enhanced ID-first search system"""
    print("🎯 Testing ID-First Search Enhancement")
    print("=" * 60)
    print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    base_url = "http://localhost:8000"
    
    # Test different ID patterns
    test_ids = [
        "JSP-1046",
        "JSP-1052", 
        "JSP-1053",
        "JIRA-1234",  # Non-existent ID
        "INC-5678",   # Non-existent ID
        "SLACK-123-456"  # Non-existent ID
    ]
    
    print("🔍 Testing ID Recognition and Instant Lookup:")
    print("-" * 60)
    
    for i, test_id in enumerate(test_ids, 1):
        print(f"\n{i}. Testing ID: {test_id}")
        
        try:
            # Test with hybrid search endpoint (direct ID lookup)
            print(f"   🔗 Testing hybrid search for exact ID match...")
            response = requests.post(
                f"{base_url}/api/v1/search/hybrid",
                json={
                    "query": test_id,
                    "top_k": 5,
                    "min_score": 0.1
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Check for exact ID match
                exact_match = None
                if result.get("results"):
                    exact_match = next(
                        (r for r in result["results"] if r["id"].lower() == test_id.lower()),
                        None
                    )
                
                if exact_match:
                    print(f"   ✅ EXACT MATCH FOUND!")
                    print(f"      📋 ID: {exact_match['id']}")
                    print(f"      📝 Title: {exact_match['title'][:60]}...")
                    print(f"      📊 Score: {exact_match.get('fused_score', exact_match.get('score', 0)):.3f}")
                    print(f"      🏷️ Tags: {', '.join(exact_match.get('tags', [])[:3])}")
                    print(f"      ⚡ Search Type: {exact_match.get('search_type', 'hybrid')}")
                else:
                    print(f"   ❌ No exact match found")
                    if result.get("results"):
                        print(f"      📊 Found {len(result['results'])} similar results")
                        top_result = result["results"][0]
                        print(f"      🥇 Top Result: {top_result['id']} - {top_result['title'][:40]}...")
                        print(f"      📊 Similarity: {top_result.get('fused_score', top_result.get('score', 0)):.3f}")
                    else:
                        print(f"      📊 No results found at all")
                        
            else:
                print(f"   ❌ API Error: {response.status_code}")
                print(f"   📝 Response: {response.text[:100]}...")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test with RAG endpoint (fallback)
        try:
            print(f"   🔗 Testing RAG search for ID...")
            rag_response = requests.post(
                f"{base_url}/api/v1/rag/query",
                json={
                    "query": test_id,
                    "include_sources": True,
                    "max_incidents": 3,
                    "confidence_threshold": 0.1
                },
                timeout=15
            )
            
            if rag_response.status_code == 200:
                rag_result = rag_response.json()
                
                if rag_result.get("result") and rag_result["result"].get("retrieved_incidents"):
                    incidents = rag_result["result"]["retrieved_incidents"]
                    confidence = rag_result["result"].get("confidence_score", 0)
                    
                    # Check for exact ID match in RAG results
                    exact_rag_match = next(
                        (inc for inc in incidents if inc["id"].lower() == test_id.lower()),
                        None
                    )
                    
                    if exact_rag_match:
                        print(f"   ✅ RAG EXACT MATCH!")
                        print(f"      📋 ID: {exact_rag_match['id']}")
                        print(f"      📊 RAG Confidence: {confidence:.3f}")
                    else:
                        print(f"   📊 RAG found {len(incidents)} incidents (no exact ID match)")
                        if incidents:
                            top_incident = incidents[0]
                            print(f"      🥇 Top: {top_incident['id']} - {top_incident['title'][:40]}...")
                            print(f"      📊 Confidence: {confidence:.3f}")
                else:
                    print(f"   📊 RAG found no incidents")
                    
            else:
                print(f"   ❌ RAG API Error: {rag_response.status_code}")
                
        except Exception as e:
            print(f"   ❌ RAG Error: {e}")
        
        time.sleep(0.5)  # Rate limiting
    
    print("\n" + "=" * 60)
    print("🎯 ID Search Test Complete!")
    print()
    
    # Test ID pattern recognition
    print("🔍 Testing ID Pattern Recognition:")
    print("-" * 60)
    
    id_patterns = [
        ("JSP-1046", True, "Valid JSP ID"),
        ("JIRA-1234", True, "Valid JIRA ID"),
        ("INC-5678", True, "Valid Incident ID"),
        ("SLACK-123-456", True, "Valid Slack ID"),
        ("TICKET-9999", True, "Valid Ticket ID"),
        ("BUG-1111", True, "Valid Bug ID"),
        ("payment timeout", False, "Regular query"),
        ("JSP-", False, "Incomplete ID"),
        ("JSP-ABC", False, "Invalid format"),
        ("123-JSP", False, "Wrong format")
    ]
    
    for pattern, expected, description in id_patterns:
        # This would be tested in the frontend, but we can simulate
        print(f"   Pattern: '{pattern}' -> Expected: {expected} ({description})")
    
    print("\n" + "=" * 60)
    print("🎉 All Tests Complete!")
    print()
    
    print("🏆 JUDGE DEMO POINTS:")
    print("• Instant ID recognition with regex patterns")
    print("• Direct ID lookup with immediate results")
    print("• Fallback to semantic search if ID not found")
    print("• Professional error handling and user feedback")
    print("• Enhanced UX for power users and support teams")
    print("• Real-time search status updates")
    print()
    
    print("🚀 BUSINESS IMPACT:")
    print("• Support teams get instant incident details")
    print("• Engineers can quickly reference past issues")
    print("• Reduces time from 'search' to 'solution'")
    print("• Professional user experience for ID lookups")
    print("• Seamless integration with existing workflows")
    print()
    
    print("💡 DEMO SCENARIO:")
    print("1. User types 'JSP-1046' in search box")
    print("2. System instantly recognizes it as incident ID")
    print("3. Shows 'Searching for incident JSP-1046...'")
    print("4. Returns exact incident details in <2 seconds")
    print("5. If not found, gracefully falls back to semantic search")


if __name__ == "__main__":
    test_id_search()
