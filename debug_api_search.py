#!/usr/bin/env python3
"""
Debug script to test API search functionality
"""

import asyncio
import os
from dotenv import load_dotenv

# Set up environment
os.environ.setdefault('PYTHONPATH', '.')
load_dotenv()

from app.services.ai_service import ai_service

async def debug_api_search():
    print("🔍 Debug API Search")
    print("=" * 50)
    
    query = "UPI payment failed"
    print(f"\n🔍 Testing search for: '{query}'")
    
    try:
        # Generate embedding for query (same as API does)
        print("1. Generating embedding...")
        query_embedding = await ai_service.embed_text(query)
        print(f"   ✅ Generated embedding with dimension: {len(query_embedding)}")
        
        # Search vector database (same as API does)
        print("2. Searching vector database...")
        results = await ai_service.search_similar(
            query_embedding=query_embedding,
            top_k=3,
            similarity_threshold=0.0,  # Same as API default
            filters=None
        )
        
        print(f"   📊 Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"     {i}. {result.get('title', 'No title')} (Score: {result.get('score', 0):.3f})")
            print(f"        ID: {result.get('id', 'N/A')}")
            print(f"        Description: {result.get('description', 'N/A')[:100]}...")
            print()
        
        # Check index stats
        print("3. Checking index stats...")
        stats = await ai_service.get_index_stats()
        print(f"   Total vectors: {stats.get('total_vectors', 0)}")
        print(f"   Dimension: {stats.get('dimension', 0)}")
        
        return results
        
    except Exception as e:
        print(f"❌ Error in debug search: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    asyncio.run(debug_api_search())
