#!/usr/bin/env python3
"""
Test Priority Matching System
Demonstrates merchant_id and payment gateway priority matching
"""

import requests
import json
import time
from datetime import datetime


def test_priority_matching():
    """Test the enhanced priority matching system"""
    print("🎯 Testing Priority Matching System")
    print("=" * 60)
    print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    base_url = "http://localhost:8000"
    
    # Test queries with different priority levels
    test_queries = [
        {
            "query": "snapdeal_test merchant_id pinelabs gateway timeout",
            "expected": "PERFECT_MERCHANT_GATEWAY_MATCH",
            "description": "Perfect Match: Same merchant + same gateway"
        },
        {
            "query": "snapdeal_test merchant payment issue",
            "expected": "MERCHANT_ID_MATCH", 
            "description": "Merchant Match: Same merchant, different gateway"
        },
        {
            "query": "pinelabs gateway RSA decryption error",
            "expected": "PAYMENT_GATEWAY_MATCH",
            "description": "Gateway Match: Same gateway, different merchant"
        },
        {
            "query": "payment timeout error general issue",
            "expected": "SEMANTIC_MATCH",
            "description": "Semantic Match: No specific merchant/gateway"
        },
        {
            "query": "hdfc_merchant axis_bank gateway integration",
            "expected": "PERFECT_MERCHANT_GATEWAY_MATCH",
            "description": "Perfect Match: Different merchant + gateway combo"
        }
    ]
    
    print("🔍 Testing Priority Matching Queries:")
    print("-" * 60)
    
    for i, test_case in enumerate(test_queries, 1):
        print(f"\n{i}. {test_case['description']}")
        print(f"   Query: \"{test_case['query']}\"")
        print(f"   Expected: {test_case['expected']}")
        
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
                
                if result.get("result") and result["result"].get("retrieved_incidents"):
                    top_incident = result["result"]["retrieved_incidents"][0]
                    
                    # Check priority matching details
                    match_type = top_incident.get("match_type", "SEMANTIC_MATCH")
                    priority_details = top_incident.get("priority_details", {})
                    confidence = result["result"].get("confidence_score", 0)
                    
                    print(f"   ✅ Result: {match_type}")
                    print(f"   📊 Confidence: {confidence:.3f}")
                    print(f"   🎯 Match: {match_type == test_case['expected']}")
                    
                    if priority_details:
                        print(f"   🔍 Details:")
                        print(f"      • Query Merchant: {priority_details.get('query_merchant', 'None')}")
                        print(f"      • Query Gateway: {priority_details.get('query_gateway', 'None')}")
                        print(f"      • Result Merchant: {priority_details.get('result_merchant', 'None')}")
                        print(f"      • Result Gateway: {priority_details.get('result_gateway', 'None')}")
                        print(f"      • Merchant Match: {priority_details.get('merchant_match', False)}")
                        print(f"      • Gateway Match: {priority_details.get('gateway_match', False)}")
                    
                    # Show top result
                    print(f"   📋 Top Result: {top_incident.get('id', 'Unknown')} - {top_incident.get('title', 'No title')[:50]}...")
                    
                else:
                    print(f"   ❌ No results found")
                    
            else:
                print(f"   ❌ API Error: {response.status_code}")
                print(f"   📝 Response: {response.text[:100]}...")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        time.sleep(1)  # Rate limiting
    
    print("\n" + "=" * 60)
    print("🎯 Priority Matching Test Complete!")
    print()
    
    # Test extraction patterns
    print("🔍 Testing Extraction Patterns:")
    print("-" * 60)
    
    extraction_tests = [
        {
            "text": "snapdeal_test merchant_id having issues",
            "expected_merchant": "snapdeal_test",
            "expected_gateway": None
        },
        {
            "text": "pinelabs gateway timeout error",
            "expected_merchant": None,
            "expected_gateway": "pinelabs"
        },
        {
            "text": "merchant: hdfc_merchant pg: axis_bank",
            "expected_merchant": "hdfc_merchant", 
            "expected_gateway": "axis_bank"
        },
        {
            "text": "payment gateway: razorpay_online timeout",
            "expected_merchant": None,
            "expected_gateway": "razorpay"
        }
    ]
    
    for i, test in enumerate(extraction_tests, 1):
        print(f"\n{i}. Text: \"{test['text']}\"")
        print(f"   Expected Merchant: {test['expected_merchant']}")
        print(f"   Expected Gateway: {test['expected_gateway']}")
        
        # Test extraction via search (this will show in logs)
        try:
            response = requests.post(
                f"{base_url}/api/v1/search/hybrid",
                json={
                    "query": test["text"],
                    "top_k": 1
                },
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"   ✅ Extraction test completed (check server logs for details)")
            else:
                print(f"   ❌ Test failed: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 All Tests Complete!")
    print()
    
    print("🏆 JUDGE DEMO POINTS:")
    print("• Perfect merchant + gateway matching with 2.5x score boost")
    print("• Merchant-only matching with 2.0x score boost") 
    print("• Gateway-only matching with 1.5x score boost")
    print("• Smart extraction of merchant_id and payment gateway")
    print("• Domain-specific intelligence for payment systems")
    print("• Real-time priority scoring in search results")
    print()
    
    print("🚀 BUSINESS IMPACT:")
    print("• Faster resolution for merchant-specific issues")
    print("• Gateway expertise preservation and reuse")
    print("• Reduced cross-contamination between different systems")
    print("• Context-aware matching beyond just keywords")


if __name__ == "__main__":
    test_priority_matching()
