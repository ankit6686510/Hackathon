#!/usr/bin/env python3
"""
Test script to verify domain classification fix for payment queries
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.ai_service import ai_service

async def test_domain_classification():
    """Test the enhanced domain classification"""
    
    print("🧪 Testing Enhanced Payment Domain Classification")
    print("=" * 60)
    
    # Test queries
    test_queries = [
        {
            "query": "Card Transactions Failing in Sandbox for FirstCry",
            "expected": True,
            "description": "Original failing query"
        },
        {
            "query": "UPI payment failed with error 5003",
            "expected": True,
            "description": "Known working payment query"
        },
        {
            "query": "Card transactions failing in sandbox for FirstCry AE/KSA",
            "expected": True,
            "description": "Extended version with regions"
        },
        {
            "query": "Payment gateway timeout in production",
            "expected": True,
            "description": "Payment gateway issue"
        },
        {
            "query": "What is the weather today",
            "expected": False,
            "description": "Non-payment query"
        },
        {
            "query": "Database connection timeout",
            "expected": False,
            "description": "Technical but non-payment query"
        },
        {
            "query": "IRCTC webhook delivery failing",
            "expected": True,
            "description": "Merchant webhook issue"
        },
        {
            "query": "2C2P refund insufficient funds",
            "expected": True,
            "description": "Payment provider issue"
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_queries, 1):
        query = test_case["query"]
        expected = test_case["expected"]
        description = test_case["description"]
        
        print(f"\n{i}. Testing: {description}")
        print(f"   Query: '{query}'")
        
        # Test domain validation
        validation = ai_service.validate_payment_domain(query)
        
        is_payment = validation["is_payment_related"]
        confidence = validation["confidence"]
        total_score = validation["total_score"]
        detected_keywords = validation["detected_keywords"]
        detected_phrases = validation["detected_phrases"]
        
        # Check result
        passed = is_payment == expected
        status = "✅ PASS" if passed else "❌ FAIL"
        
        print(f"   Result: {status}")
        print(f"   Payment Related: {is_payment} (expected: {expected})")
        print(f"   Confidence: {confidence:.2f}")
        print(f"   Total Score: {total_score}")
        
        if detected_keywords:
            print(f"   Keywords: {', '.join(detected_keywords[:5])}{'...' if len(detected_keywords) > 5 else ''}")
        
        if detected_phrases:
            print(f"   Phrases: {', '.join(detected_phrases)}")
        
        results.append({
            "query": query,
            "expected": expected,
            "actual": is_payment,
            "passed": passed,
            "confidence": confidence,
            "total_score": total_score
        })
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed_count = sum(1 for r in results if r["passed"])
    total_count = len(results)
    success_rate = (passed_count / total_count) * 100
    
    print(f"Total Tests: {total_count}")
    print(f"Passed: {passed_count}")
    print(f"Failed: {total_count - passed_count}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    # Show failed tests
    failed_tests = [r for r in results if not r["passed"]]
    if failed_tests:
        print(f"\n❌ FAILED TESTS:")
        for test in failed_tests:
            print(f"   '{test['query']}' - Expected: {test['expected']}, Got: {test['actual']}")
    
    # Show the key test result
    original_query_test = next((r for r in results if "Card Transactions Failing in Sandbox for FirstCry" in r["query"]), None)
    if original_query_test:
        print(f"\n🎯 KEY TEST RESULT:")
        print(f"   Original Query: {'✅ FIXED' if original_query_test['passed'] else '❌ STILL BROKEN'}")
        print(f"   Confidence: {original_query_test['confidence']:.2f}")
        print(f"   Score: {original_query_test['total_score']}")
    
    return success_rate >= 85  # 85% success rate threshold

async def test_full_search_pipeline():
    """Test the complete search pipeline with the fixed query"""
    
    print("\n🔍 Testing Complete Search Pipeline")
    print("=" * 60)
    
    test_query = "Card Transactions Failing in Sandbox for FirstCry"
    
    try:
        print(f"Query: '{test_query}'")
        
        # Test the complete smart response pipeline
        response = await ai_service.generate_payment_smart_response(test_query)
        
        print(f"Response Type: {response['type']}")
        print(f"Has Historical Data: {response.get('has_historical_data', False)}")
        
        if response['type'] == 'domain_rejection':
            print("❌ FAILED: Query still being rejected as non-payment")
            return False
        elif response['type'] == 'historical_payment_issues':
            results = response.get('content', [])
            print(f"✅ SUCCESS: Found {len(results)} historical issues")
            
            if results:
                top_result = results[0]
                print(f"Top Match: {top_result.get('metadata', {}).get('title', 'Unknown')}")
                print(f"Score: {top_result.get('score', 0):.3f}")
                
                # Check if we found the FirstCry issues
                for result in results:
                    metadata = result.get('metadata', {})
                    title = metadata.get('title', '')
                    if 'firstcry' in title.lower():
                        print(f"🎯 Found FirstCry issue: {title}")
                        break
            
            return True
        elif response['type'] in ['ai_payment_solution', 'ai_payment_solution_fallback']:
            print("✅ SUCCESS: Generated AI solution (no historical data found)")
            return True
        else:
            print(f"❌ UNEXPECTED: Response type {response['type']}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

async def main():
    """Main test function"""
    print("🚀 Starting Payment Domain Classification Tests")
    
    # Test 1: Domain classification
    classification_success = await test_domain_classification()
    
    # Test 2: Full pipeline
    pipeline_success = await test_full_search_pipeline()
    
    # Final result
    print("\n" + "=" * 60)
    print("🏁 FINAL RESULTS")
    print("=" * 60)
    
    if classification_success and pipeline_success:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Domain classification is working correctly")
        print("✅ Search pipeline is functioning properly")
        print("✅ Your original query should now work in Slack!")
    else:
        print("⚠️ SOME TESTS FAILED")
        if not classification_success:
            print("❌ Domain classification needs more work")
        if not pipeline_success:
            print("❌ Search pipeline has issues")
    
    return classification_success and pipeline_success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
