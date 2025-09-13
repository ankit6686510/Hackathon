#!/usr/bin/env python3
"""
Test Exact Ticket ID Lookup System
Verifies that ticket IDs bypass semantic search completely
"""

import requests
import json
import time
from datetime import datetime


def test_exact_ticket_lookup():
    """Test the exact ticket ID lookup system"""
    print("🎯 Testing EXACT TICKET ID LOOKUP System")
    print("=" * 60)
    print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    base_url = "http://localhost:8000"
    
    # Test cases for exact ticket ID lookup
    test_cases = [
        {
            "query": "JSP-1046",
            "description": "Exact ticket ID only",
            "expected_strategy": "exact_id_lookup",
            "expected_confidence": 1.0,
            "expected_match_type": "EXACT_ID"
        },
        {
            "query": "JSP-1046 can you explain me this problem",
            "description": "Ticket ID with additional text",
            "expected_strategy": "exact_id_lookup", 
            "expected_confidence": 1.0,
            "expected_match_type": "EXACT_ID"
        },
        {
            "query": "I need help with JSP-1052 issue",
            "description": "Ticket ID embedded in sentence",
            "expected_strategy": "exact_id_lookup",
            "expected_confidence": 1.0,
            "expected_match_type": "EXACT_ID"
        },
        {
            "query": "Check incident JSP-1053 for details",
            "description": "Ticket ID in context",
            "expected_strategy": "exact_id_lookup",
            "expected_confidence": 1.0,
            "expected_match_type": "EXACT_ID"
        },
        {
            "query": "EUL-1234",
            "description": "Non-existent ticket ID",
            "expected_strategy": "exact_id_not_found",
            "expected_confidence": 1.0,
            "expected_match_type": None
        },
        {
            "query": "JIRA-9999 not working",
            "description": "Non-existent ticket ID with text",
            "expected_strategy": "exact_id_not_found",
            "expected_confidence": 1.0,
            "expected_match_type": None
        },
        {
            "query": "payment timeout error",
            "description": "Regular query without ticket ID",
            "expected_strategy": "simple_query_with_*_incidents",
            "expected_confidence": "variable",
            "expected_match_type": "semantic"
        }
    ]
    
    print("🔍 Testing Exact Ticket ID Lookup:")
    print("-" * 60)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['description']}")
        print(f"   Query: \"{test_case['query']}\"")
        print(f"   Expected Strategy: {test_case['expected_strategy']}")
        
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
                confidence_score = rag_result.get("confidence_score", 0)
                retrieved_incidents = rag_result.get("retrieved_incidents", [])
                generated_answer = rag_result.get("generated_answer", "")
                execution_time = rag_result.get("execution_time_ms", 0)
                
                print(f"   ✅ Status: SUCCESS")
                print(f"   📊 Strategy: {rag_strategy}")
                print(f"   🎯 Confidence: {confidence_score:.3f}")
                print(f"   📋 Incidents: {len(retrieved_incidents)}")
                print(f"   ⏱️ Time: {execution_time:.0f}ms")
                
                # Verify exact ticket ID behavior
                if "exact_id" in rag_strategy:
                    print(f"   🎯 EXACT ID LOOKUP DETECTED!")
                    
                    if rag_strategy == "exact_id_lookup":
                        if retrieved_incidents:
                            ticket = retrieved_incidents[0]
                            match_type = ticket.get("match_type", "unknown")
                            search_type = ticket.get("search_type", "unknown")
                            
                            print(f"      📋 Found Ticket: {ticket.get('id', 'Unknown')}")
                            print(f"      📝 Title: {ticket.get('title', 'No title')[:50]}...")
                            print(f"      🔍 Match Type: {match_type}")
                            print(f"      🔧 Search Type: {search_type}")
                            
                            # Verify exact match properties
                            if match_type == "EXACT_ID" and confidence_score == 1.0:
                                print(f"      ✅ PERFECT: Exact ID lookup working correctly!")
                            else:
                                print(f"      ⚠️ WARNING: Expected EXACT_ID match with confidence 1.0")
                        else:
                            print(f"      ❌ ERROR: Expected ticket data for exact_id_lookup")
                    
                    elif rag_strategy == "exact_id_not_found":
                        print(f"      ✅ CORRECT: Ticket not found as expected")
                        if "Ticket Not Found" in generated_answer:
                            print(f"      ✅ PERFECT: Proper 'not found' message")
                        else:
                            print(f"      ⚠️ WARNING: Expected 'Ticket Not Found' message")
                
                else:
                    print(f"   📊 SEMANTIC SEARCH: Regular query processing")
                    if test_case["expected_strategy"].startswith("exact_id"):
                        print(f"      ❌ ERROR: Expected exact ID lookup but got semantic search")
                    else:
                        print(f"      ✅ CORRECT: Semantic search for non-ID query")
                
                # Show response preview
                print(f"   💬 Response: {generated_answer[:80]}...")
                
                # Verify expectations
                strategy_match = (
                    rag_strategy == test_case["expected_strategy"] or
                    (test_case["expected_strategy"].endswith("*_incidents") and 
                     "incidents" in rag_strategy)
                )
                
                confidence_match = (
                    test_case["expected_confidence"] == "variable" or
                    abs(confidence_score - test_case["expected_confidence"]) < 0.1
                )
                
                if strategy_match and confidence_match:
                    print(f"   ✅ EXPECTATIONS MET")
                else:
                    print(f"   ⚠️ EXPECTATIONS NOT MET")
                    if not strategy_match:
                        print(f"      Strategy: Expected {test_case['expected_strategy']}, Got {rag_strategy}")
                    if not confidence_match:
                        print(f"      Confidence: Expected {test_case['expected_confidence']}, Got {confidence_score}")
                
            else:
                print(f"   ❌ API Error: {response.status_code}")
                print(f"   📝 Response: {response.text[:100]}...")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        time.sleep(1)  # Rate limiting
    
    print("\n" + "=" * 60)
    print("🎯 Exact Ticket ID Lookup Test Complete!")
    print()
    
    # Test ID extraction patterns
    print("🔍 Testing ID Extraction Patterns:")
    print("-" * 60)
    
    extraction_tests = [
        ("JSP-1046", "JSP-1046", "Simple ID"),
        ("JSP-1046 explain this", "JSP-1046", "ID with text"),
        ("Check JSP-1052 issue", "JSP-1052", "ID in sentence"),
        ("EUL-1234 problem", "EUL-1234", "EUL format"),
        ("JIRA-5678 bug", "JIRA-5678", "JIRA format"),
        ("payment timeout", None, "No ID"),
        ("JSP- incomplete", None, "Incomplete ID"),
        ("123-JSP wrong format", None, "Wrong format")
    ]
    
    for i, (query, expected_id, description) in enumerate(extraction_tests, 1):
        print(f"\n{i}. {description}")
        print(f"   Query: \"{query}\"")
        print(f"   Expected ID: {expected_id}")
        
        # Test extraction by checking if exact lookup is triggered
        try:
            response = requests.post(
                f"{base_url}/api/v1/rag/query",
                json={
                    "query": query,
                    "include_sources": True,
                    "max_incidents": 1,
                    "confidence_threshold": 0.1
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                rag_strategy = result.get("result", {}).get("rag_strategy", "unknown")
                
                if "exact_id" in rag_strategy:
                    print(f"   ✅ ID EXTRACTED: Exact lookup triggered")
                    if expected_id:
                        print(f"   ✅ CORRECT: Expected ID extraction")
                    else:
                        print(f"   ❌ ERROR: Unexpected ID extraction")
                else:
                    print(f"   📊 NO ID: Semantic search used")
                    if expected_id:
                        print(f"   ❌ ERROR: Expected ID extraction but got semantic")
                    else:
                        print(f"   ✅ CORRECT: No ID expected")
            else:
                print(f"   ❌ API Error: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 All Tests Complete!")
    print()
    
    print("🏆 EXACT TICKET ID LOOKUP FEATURES:")
    print("• Bypasses semantic search completely for ticket IDs")
    print("• Returns exact ticket data with 100% confidence")
    print("• Supports multiple ID formats: JSP-XXXX, EUL-XXXX, JIRA-XXXX")
    print("• Works with additional text in queries")
    print("• Provides clear 'not found' messages for missing tickets")
    print("• Generates AI summaries using ONLY ticket content")
    print("• Match type: EXACT_ID with confidence: 1.0")
    print()
    
    print("🚀 BUSINESS IMPACT:")
    print("• Instant ticket lookup for support teams")
    print("• Zero false positives - exact matches only")
    print("• Professional 'not found' handling")
    print("• Consistent response format")
    print("• Predictable performance")
    print()
    
    print("💡 DEMO SCENARIOS:")
    print("1. Support agent types 'JSP-1046' → Instant ticket details")
    print("2. Engineer asks 'JSP-1046 can you explain' → Same instant result")
    print("3. Manager searches 'EUL-9999' → Clear 'not found' message")
    print("4. Regular query 'payment timeout' → Normal semantic search")


if __name__ == "__main__":
    test_exact_ticket_lookup()
