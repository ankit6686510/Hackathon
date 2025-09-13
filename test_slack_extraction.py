#!/usr/bin/env python3
"""
Test Slack Extraction Functionality
Demonstrates the live learning capability from Slack #issues channel
"""

import asyncio
import json
import os
from datetime import datetime

# Set up environment
os.environ.setdefault('PYTHONPATH', '.')

from app.services.slack_extractor import extract_and_learn_from_slack, slack_extractor


async def test_slack_connection():
    """Test connection to Slack #issues channel"""
    print("🔗 Testing Slack Connection...")
    print("=" * 50)
    
    # Check environment variables
    required_vars = ["SLACK_BOT_TOKEN", "SLACK_APP_TOKEN", "SLACK_SIGNING_SECRET"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("\nPlease set these in your .env file:")
        for var in missing_vars:
            print(f"  {var}=your_token_here")
        return False
    
    print("✅ All Slack environment variables are set")
    
    # Test connection
    try:
        initialized = await slack_extractor.initialize()
        if initialized:
            print(f"✅ Connected to {slack_extractor.issues_channel} channel")
            print(f"📋 Channel ID: {slack_extractor.issues_channel_id}")
            return True
        else:
            print("❌ Failed to connect to #issues channel")
            print("💡 Make sure:")
            print("   • #issues channel exists in your workspace")
            print("   • Bot is invited to the channel")
            print("   • Bot has proper permissions")
            return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False


async def test_extraction():
    """Test extracting incidents from Slack"""
    print("\n🔍 Testing Incident Extraction...")
    print("=" * 50)
    
    try:
        # Extract from last 24 hours
        result = await extract_and_learn_from_slack(hours_back=24)
        
        print(f"📊 Extraction Results:")
        print(f"   • Success: {result['success']}")
        print(f"   • Incidents Found: {result['incidents_found']}")
        print(f"   • Incidents Added: {result['incidents_added']}")
        
        if result.get('error'):
            print(f"   • Error: {result['error']}")
        
        if result.get('incidents'):
            print(f"\n📋 Extracted Incidents:")
            for i, incident in enumerate(result['incidents'], 1):
                print(f"   {i}. {incident['title']}")
                print(f"      Confidence: {incident['confidence']:.2f}")
                print(f"      Status: {incident['status']}")
                print(f"      Tags: {', '.join(incident['tags'])}")
                print()
        
        return result['success']
        
    except Exception as e:
        print(f"❌ Extraction error: {e}")
        return False


async def test_api_endpoints():
    """Test the API endpoints"""
    print("\n🌐 Testing API Endpoints...")
    print("=" * 50)
    
    import requests
    
    base_url = "http://localhost:8000"
    
    # Test endpoints
    endpoints = [
        ("/api/v1/slack/channel-info", "GET"),
        ("/api/v1/slack/monitoring-status", "GET"),
        ("/api/v1/slack/test-extraction", "POST")
    ]
    
    for endpoint, method in endpoints:
        try:
            url = f"{base_url}{endpoint}"
            print(f"🔗 Testing {method} {endpoint}")
            
            if method == "GET":
                response = requests.get(url, timeout=10)
            else:
                response = requests.post(url, json={}, timeout=30)
            
            if response.status_code == 200:
                print(f"   ✅ Success: {response.status_code}")
                data = response.json()
                if 'message' in data:
                    print(f"   📝 Message: {data['message']}")
            else:
                print(f"   ❌ Failed: {response.status_code}")
                print(f"   📝 Response: {response.text[:100]}...")
                
        except requests.exceptions.ConnectionError:
            print(f"   ❌ Connection failed - is the server running on {base_url}?")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()


async def demo_live_learning():
    """Demonstrate the live learning capability"""
    print("\n🎯 Live Learning Demo")
    print("=" * 50)
    
    print("This is how your system will work:")
    print()
    
    print("1. 👨‍💻 Engineer posts in #issues:")
    print('   "Payment gateway timeout on HDFC bank, getting 502 errors"')
    print()
    
    print("2. 🤖 AI automatically extracts:")
    print("   • Title: Payment Gateway Timeout - HDFC Bank 502 Error")
    print("   • Tags: [Payment, Gateway, Timeout, HDFC, 502-Error]")
    print("   • Status: reported")
    print("   • Confidence: 0.85")
    print()
    
    print("3. 🔄 System automatically:")
    print("   • Adds to knowledge base")
    print("   • Rebuilds search indices")
    print("   • Makes it searchable immediately")
    print()
    
    print("4. 🔍 Next engineer searches:")
    print('   "HDFC timeout" → Gets instant results!')
    print()
    
    print("🏆 JUDGE IMPACT:")
    print("   • Zero-effort knowledge capture")
    print("   • Real-time learning from Slack")
    print("   • Tribal knowledge preservation")
    print("   • No behavior change needed")


async def main():
    """Main test function"""
    print("🚀 SherlockAI Slack Integration Test")
    print("=" * 50)
    print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test 1: Connection
    connection_ok = await test_slack_connection()
    
    if connection_ok:
        # Test 2: Extraction
        extraction_ok = await test_extraction()
        
        # Test 3: API endpoints (if server is running)
        await test_api_endpoints()
    
    # Test 4: Demo
    await demo_live_learning()
    
    print("\n🎉 Test Complete!")
    print("=" * 50)
    
    if connection_ok:
        print("✅ Your Slack integration is ready!")
        print("\n🚀 Next Steps:")
        print("1. Start your FastAPI server: python -m app.main")
        print("2. Test extraction: POST /api/v1/slack/extract")
        print("3. Start monitoring: POST /api/v1/slack/start-monitoring")
        print("4. Demo to judges: Show live learning from Slack!")
    else:
        print("❌ Slack integration needs setup")
        print("\n🔧 Setup Steps:")
        print("1. Create Slack app at https://api.slack.com/apps")
        print("2. Add bot tokens to .env file")
        print("3. Create #issues channel")
        print("4. Invite bot to channel")
        print("5. Run this test again")


if __name__ == "__main__":
    asyncio.run(main())
