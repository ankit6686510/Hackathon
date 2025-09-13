#!/usr/bin/env python3
"""
Test script to verify domain validation fix
"""

import asyncio
import sys
import os

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

from app.services.ai_service import ai_service

async def test_domain_validation():
    """Test the domain validation with the problematic query"""
    
    test_query = "merchant snapdeal (MID: snapdeal_test) is integrating the pinelabs_online gateway and are facing the INTERNAL_SERVER_ERROR in the /txns call and hence are blocked on testing. Could you please help debug this. Logs in the thread."
    
    print("🔍 Testing Domain Validation Fix")
    print("=" * 50)
    print(f"Query: {test_query}")
    print()
    
    # Test domain validation
    domain_result = ai_service.validate_payment_domain(test_query)
    
    print("📊 Domain Validation Results:")
    print(f"  ✅ Is Payment Related: {domain_result['is_payment_related']}")
    print(f"  📈 Payment Score: {domain_result['payment_score']}")
    print(f"  📝 Phrase Score: {domain_result['phrase_score']}")
    print(f"  🏦 Bank Code Found: {domain_result['bank_code_found']}")
    print(f"  🎯 Total Score: {domain_result['total_score']}")
    print(f"  💯 Confidence: {domain_result['confidence']:.2f}")
    print()
    
    print("🔍 Detected Keywords:")
    for keyword in domain_result['detected_keywords'][:10]:  # Show first 10
        print(f"  • {keyword}")
    if len(domain_result['detected_keywords']) > 10:
        print(f"  ... and {len(domain_result['detected_keywords']) - 10} more")
    print()
    
    print("📝 Detected Phrases:")
    for phrase in domain_result['detected_phrases']:
        print(f"  • {phrase}")
    print()
    
    # Test the smart response
    print("🤖 Testing Smart Response...")
    try:
        smart_response = await ai_service.generate_payment_smart_response(test_query)
        print(f"  Response Type: {smart_response['type']}")
        print(f"  Has Historical Data: {smart_response.get('has_historical_data', False)}")
        
        if smart_response['type'] == 'historical_payment_issues':
            print(f"  Found {len(smart_response['content'])} historical issues")
            for i, issue in enumerate(smart_response['content'][:3]):
                print(f"    {i+1}. {issue.get('id', 'Unknown')} - Score: {issue.get('score', 0):.3f}")
        elif smart_response['type'] == 'domain_rejection':
            print("  ❌ Query was rejected as non-payment related")
        else:
            print(f"  Response: {smart_response['type']}")
            
    except Exception as e:
        print(f"  ❌ Error testing smart response: {e}")
    
    print()
    print("✅ Domain validation test completed!")
    
    if domain_result['is_payment_related']:
        print("🎉 SUCCESS: Query is now recognized as payment-related!")
    else:
        print("❌ FAILED: Query is still being rejected")

if __name__ == "__main__":
    asyncio.run(test_domain_validation())
