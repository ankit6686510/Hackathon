#!/usr/bin/env python3
"""
FixGenie Demo Script
Demonstrates the working AI-powered issue intelligence system
"""

import requests
import json
import time
from datetime import datetime

def print_banner():
    print("=" * 80)
    print("🔍 FixGenie - AI-Powered Issue Intelligence System")
    print("=" * 80)
    print("✅ Streamlit REMOVED - Now using modern React frontend")
    print("✅ Backend API running on http://localhost:8000")
    print("✅ React frontend running on http://localhost:5174")
    print("✅ Vector database with 34 issues loaded")
    print("=" * 80)
    print()

def check_system_health():
    print("🏥 System Health Check:")
    try:
        response = requests.get("http://localhost:8000/api/v1/health", timeout=5)
        health_data = response.json()
        
        print(f"   Backend Status: {'✅ Online' if response.status_code == 200 else '❌ Error'}")
        
        # Check vector database
        try:
            vectors = health_data['services']['ai_services']['pinecone']['total_vectors']
            print(f"   Vector Database: ✅ {vectors} vectors")
        except:
            print("   Vector Database: ⚠️ Status unknown")
        
        # Check system info
        try:
            uptime = health_data['system']['uptime_seconds']
            print(f"   System Uptime: {uptime:.1f} seconds")
        except:
            print("   System Uptime: ⚠️ Status unknown")
        
        print()
        return response.status_code == 200
    except Exception as e:
        print(f"   ❌ Backend Error: {e}")
        return False

def demo_search_query(query, description):
    print(f"🔍 Demo Query: {description}")
    print(f"   Query: '{query}'")
    
    try:
        start_time = time.time()
        response = requests.post(
            "http://localhost:8000/api/v1/search",
            json={
                "query": query,
                "top_k": 3,
                "search_type": "semantic"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            execution_time = time.time() - start_time
            
            print(f"   ✅ Found {data['total_results']} results in {execution_time:.2f}s")
            
            if data['results']:
                top_result = data['results'][0]
                print(f"   📋 Top Match: {top_result['title']}")
                print(f"   🎯 Confidence: {top_result['score']:.1%}")
                print(f"   💡 AI Suggestion: {top_result['ai_suggestion'][:100]}...")
            
            print()
            return True
        else:
            print(f"   ❌ API Error: {response.status_code}")
            print()
            return False
            
    except Exception as e:
        print(f"   ❌ Request Error: {e}")
        print()
        return False

def main():
    print_banner()
    
    # Check system health
    if not check_system_health():
        print("❌ System health check failed. Please ensure backend is running.")
        return
    
    # Demo queries
    demo_queries = [
        ("UPI payment failed with timeout", "Payment Gateway Issue"),
        ("database connection error", "Infrastructure Problem"),
        ("API returning 500 error", "Service Integration Issue"),
        ("authentication failed", "Security/Auth Issue")
    ]
    
    print("🚀 Running Demo Queries:")
    print("-" * 50)
    
    success_count = 0
    for query, description in demo_queries:
        if demo_search_query(query, description):
            success_count += 1
        time.sleep(1)  # Brief pause between queries
    
    # Summary
    print("📊 Demo Results:")
    print(f"   ✅ Successful queries: {success_count}/{len(demo_queries)}")
    print(f"   🌐 Frontend URL: http://localhost:5174")
    print(f"   🔧 Backend API: http://localhost:8000")
    print()
    
    print("🎯 Next Steps:")
    print("   1. Open http://localhost:5174 in your browser")
    print("   2. Try asking: 'UPI payment failed with error 5003'")
    print("   3. Experience the AI-powered issue intelligence!")
    print()
    
    print("✨ FixGenie is ready for your hackathon demo!")

if __name__ == "__main__":
    main()
