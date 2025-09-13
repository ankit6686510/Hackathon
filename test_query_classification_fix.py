#!/usr/bin/env python3
"""
Test Query Classification Fix
Verifies that ticket IDs are detected before capability queries
"""

import requests
import json
import time
from datetime import datetime


def test_query_classification_fix():
    """Test that the query classification fix is working"""
    print("🎯 Testing Query Classification Fix")
    print("=" * 60)
    print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    base_url = "http://localhost:8000"
    
    # Test cases that were failing before the fix
    test_cases = [
        {
            "query": "can you help me to solve this JSP-1030",
            "description": "Original failing case - capability words + ticket ID",
            "expected_behavior": "Should detect JSP-1030 and do ticket lookup",
            "should_not_get": "capabilities response"
        },
        {
            "query": "JSP-1030 can you explain me this problem",
            "description": "Ticket ID + capability words",
            "expected_behavior": "Should detect JSP-1030 and do ticket lookup",
            "should_not_get": "capabilities response"
        },
        {
            "query": "help me with JSP-1046 issue",
            "description": "Help request + ticket ID",
            "expected_behavior": "Should detect JSP-1046 and do ticket lookup",
            "should_not_get": "capabilities response"
        },
        {
            "query": "what can you tell me about JSP-1052",
            "description": "Capability question + ticket ID",
            "expected_behavior": "Should detect JSP-1052 and do ticket lookup",
            "should_not_get": "capabilities response"
        },
        {
            "query": "what can you do",
            "description": "Pure capability query without ticket ID",
            "expected_behavior": "Should show capabilities",
            "should_not_get": "incident search"
        },
        {
            "query": "can you help me",
            "description": "Pure help request without ticket ID",
            "expected_behavior": "Should show capabilities",
            "should_not_get": "incident search"
        }
    ]
    
    print("🔍 Testing Query Classification Priority:")
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
                
                # Extract key information
                rag_result = result.get("result", {})
                rag_strategy = rag_result.get("rag_strategy", "unknown")
                generated_answer = rag_result.get("generated_answer", "")
                retrieved_incidents = rag_result.get("retrieved_incidents", [])
                
                print(f"   ✅ Status: SUCCESS")
                print(f"   📊 Strategy: {rag_strategy}")
                print(f"   📋 Incidents: {len(retrieved_incidents)}")
                
                # Check if we got the expected behavior
                is_capabilities_response = "SherlockAI Capabilities" in generated_answer
                is_incident_search = len(retrieved_incidents) > 0 or "exact_id" in rag_strategy
                
                if is_capabilities_response:
                    print(f"   📋 RESPONSE TYPE: Capabilities")
                elif is_incident_search:
                    print(f"   🎯 RESPONSE TYPE: Incident Search")
                else:
                    print(f"   ❓ RESPONSE TYPE: Other")
                
                # Verify expectations
                if "ticket lookup" in test_case["expected_behavior"]:
                    if is_incident_search and not is_capabilities_response:
                        print(f"   ✅ CORRECT: Got incident search as expected")
                    else:
                        print(f"   ❌ WRONG: Expected incident search but got capabilities")
                        print(f"      Response preview: {generated_answer[:100]}...")
                
                elif "capabilities" in test_case["expected_behavior"]:
                    if is_capabilities_response and not is_incident_search:
                        print(f"   ✅ CORRECT: Got capabilities as expected")
                    else:
                        print(f"   ❌ WRONG: Expected capabilities but got incident search")
                        print(f"      Response preview: {generated_answer[:100]}...")
                
                # Check what we should NOT get
                if test_case["should_not_get"] == "capabilities response":
                    if is_capabilities_response:
                        print(f"   ❌ PROBLEM: Got capabilities response when we shouldn't")
                    else:
                        print(f"   ✅ GOOD: Avoided unwanted capabilities response")
                
                elif test_case["should_not_get"] == "incident search":
                    if is_incident_search:
                        print(f"   ❌ PROBLEM: Got incident search when we shouldn't")
                    else:
                        print(f"   ✅ GOOD: Avoided unwanted incident search")
                
            else:
                print(f"   ❌ API Error: {response.status_code}")
                print(f"   📝 Response: {response.text[:100]}...")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        time.sleep(1)  # Rate limiting
    
    print("\n" + "=" * 60)
    print("🎯 Query Classification Fix Test Complete!")
    print()
    
    print("🏆 EXPECTED RESULTS AFTER FIX:")
    print("✅ 'can you help me to solve this JSP-1030' → Incident search")
    print("✅ 'JSP-1030 can you explain me this problem' → Incident search")
    print("✅ 'help me with JSP-1046 issue' → Incident search")
    print("✅ 'what can you tell me about JSP-1052' → Incident search")
    print("✅ 'what can you do' → Capabilities")
    print("✅ 'can you help me' → Capabilities")
    print()
    
    print("🔧 THE FIX:")
    print("• Moved ticket ID detection BEFORE capability detection")
    print("• Added exclusion check: isCapabilityQuery() && !isIncidentID()")
    print("• Ensures ticket IDs always get priority over capability keywords")
    print("• Maintains proper capability responses for non-ID queries")
    print()
    
    print("💡 DEMO VERIFICATION:")
    print("1. Try: 'can you help me to solve this JSP-1030'")
    print("2. Should get: Incident search for JSP-1030")
    print("3. Should NOT get: Capabilities response")
    print("4. Try: 'what can you do' (without ticket ID)")
    print("5. Should get: Capabilities response")


if __name__ == "__main__":
    test_query_classification_fix()
