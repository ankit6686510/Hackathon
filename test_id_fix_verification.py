#!/usr/bin/env python3
"""
Test ID-First Search Fix Verification
Verifies that incident IDs are now properly recognized and processed
"""

import requests
import json
import time
from datetime import datetime


def test_id_fix():
    """Test that the ID-first search fix is working"""
    print("🎯 Testing ID-First Search Fix")
    print("=" * 60)
    print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    base_url = "http://localhost:8000"
    
    # Test the exact scenario that was failing
    test_cases = [
        {
            "query": "JSP-1046",
            "description": "Original failing case - should now work",
            "expected_behavior": "Should find incident and provide details"
        },
        {
            "query": "JSP-1046 can you explain me this problem",
            "description": "ID with additional text - should work",
            "expected_behavior": "Should recognize ID and search for it"
        },
        {
            "query": "JSP-1052",
            "description": "Another valid incident ID",
            "expected_behavior": "Should find incident details"
        },
        {
            "query": "JIRA-1234",
            "description": "Non-existent ID pattern",
            "expected_behavior": "Should attempt search but not find exact match"
        },
        {
            "query": "payment timeout",
            "description": "Regular payment query",
            "expected_behavior": "Should work as normal payment query"
        }
    ]
    
    print("🔍 Testing RAG Endpoint with ID Recognition:")
    print("-" * 60)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['description']}")
        print(f"   Query: \"{test_case['query']}\"")
        print(f"   Expected: {test_case['expected_behavior']}")
        
        try:
            # Test with RAG endpoint
            response = requests.post(
                f"{base_url}/api/v1/rag/query",
                json={
                    "query": test_case["query"],
                    "include_sources": True,
                    "max_incidents": 3,
                    "confidence_threshold": 0.1
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Check domain validation
                domain_validation = result.get("metadata", {}).get("domain_validation", {})
                is_payment_related = domain_validation.get("is_payment_related", False)
                is_incident_id = domain_validation.get("is_incident_id", False)
                
                print(f"   ✅ Status: SUCCESS")
                print(f"   📊 Payment Related: {is_payment_related}")
                print(f"   🆔 Incident ID: {is_incident_id}")
                print(f"   📝 Reason: {domain_validation.get('reason', 'unknown')}")
                
                # Check if we got a proper response
                rag_result = result.get("result", {})
                generated_answer = rag_result.get("generated_answer", "")
                retrieved_incidents = rag_result.get("retrieved_incidents", [])
                
                if "specialize in payment-related issues only" in generated_answer:
                    print(f"   ❌ ISSUE: Still getting domain rejection!")
                    print(f"   📝 Response: {generated_answer[:100]}...")
                else:
                    print(f"   ✅ FIXED: Got proper response")
                    print(f"   📊 Incidents Found: {len(retrieved_incidents)}")
                    if retrieved_incidents:
                        top_incident = retrieved_incidents[0]
                        print(f"   🎯 Top Result: {top_incident.get('id', 'Unknown')} - {top_incident.get('title', 'No title')[:50]}...")
                    print(f"   💬 Response: {generated_answer[:100]}...")
                
            else:
                print(f"   ❌ API Error: {response.status_code}")
                print(f"   📝 Response: {response.text[:100]}...")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        time.sleep(1)  # Rate limiting
    
    print("\n" + "=" * 60)
    print("🎯 ID Fix Verification Complete!")
    print()
    
    # Test the specific failing scenario
    print("🔍 Testing Specific Failing Scenario:")
    print("-" * 60)
    
    failing_query = "JSP-1046"
    print(f"Testing exact failing query: '{failing_query}'")
    
    try:
        response = requests.post(
            f"{base_url}/api/v1/rag/query",
            json={
                "query": failing_query,
                "include_sources": True,
                "max_incidents": 3,
                "confidence_threshold": 0.1
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            generated_answer = result.get("result", {}).get("generated_answer", "")
            
            if "specialize in payment-related issues only" in generated_answer:
                print("❌ STILL BROKEN: Getting domain rejection for incident ID")
                print("🔧 Need to check:")
                print("   • Is the server restarted?")
                print("   • Are the changes deployed?")
                print("   • Is the RAG service using the new domain check?")
            else:
                print("✅ FIXED: Incident ID is now properly recognized!")
                print(f"Response: {generated_answer[:200]}...")
        else:
            print(f"❌ API Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 Test Complete!")
    print()
    
    print("🏆 EXPECTED RESULTS:")
    print("• JSP-1046 should be recognized as incident ID")
    print("• Should bypass domain filtering")
    print("• Should search for and return incident details")
    print("• Should NOT get 'specialize in payment-related issues only' response")
    print()
    
    print("🚀 IF STILL FAILING:")
    print("• Restart the FastAPI server")
    print("• Check server logs for domain validation")
    print("• Verify RAG service is using new is_payment_domain_query method")
    print("• Test with curl to isolate frontend vs backend issues")


if __name__ == "__main__":
    test_id_fix()
