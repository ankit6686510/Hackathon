#!/usr/bin/env python3
"""
Test script to isolate the API issue
"""

import asyncio
import os
from dotenv import load_dotenv

# Set up environment
os.environ.setdefault('PYTHONPATH', '.')
load_dotenv()

from app.services.ai_service import ai_service

async def test_api_issue():
    print("🔍 Testing API Issue")
    print("=" * 50)
    
    query = "UPI payment failed"
    print(f"\n🔍 Testing search for: '{query}'")
    
    try:
        # Generate embedding for query (same as API does)
        print("1. Generating embedding...")
        query_embedding = await ai_service.embed_text(query)
        print(f"   ✅ Generated embedding with dimension: {len(query_embedding)}")
        
        # Test 1: Direct call like debug script (should work)
        print("\n2. Test 1: Direct call (like debug script)...")
        results1 = await ai_service.search_similar(
            query_embedding=query_embedding,
            top_k=3,
            similarity_threshold=0.0,
            filters=None
        )
        print(f"   📊 Found {len(results1)} results")
        
        # Test 2: Call with include_resolved_only filter (like API does)
        print("\n3. Test 2: With include_resolved_only filter...")
        vector_filters = {"status": {"$eq": "resolved"}}
        results2 = await ai_service.search_similar(
            query_embedding=query_embedding,
            top_k=3,
            similarity_threshold=0.0,
            filters=vector_filters
        )
        print(f"   📊 Found {len(results2)} results")
        
        # Test 3: Call with empty filters dict (like API might do)
        print("\n4. Test 3: With empty filters dict...")
        results3 = await ai_service.search_similar(
            query_embedding=query_embedding,
            top_k=3,
            similarity_threshold=0.0,
            filters={}
        )
        print(f"   📊 Found {len(results3)} results")
        
        # Test 4: Call with similarity threshold 0.5
        print("\n5. Test 4: With similarity threshold 0.5...")
        results4 = await ai_service.search_similar(
            query_embedding=query_embedding,
            top_k=3,
            similarity_threshold=0.5,
            filters=None
        )
        print(f"   📊 Found {len(results4)} results")
        
        return results1, results2, results3, results4
        
    except Exception as e:
        print(f"❌ Error in test: {e}")
        import traceback
        traceback.print_exc()
        return [], [], [], []

if __name__ == "__main__":
    asyncio.run(test_api_issue())
