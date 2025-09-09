#!/usr/bin/env python3
"""
Debug script to test Pinecone search functionality
"""

import asyncio
import os
from dotenv import load_dotenv
import google.generativeai as genai
from pinecone import Pinecone

load_dotenv()

async def debug_search():
    print("🔍 FixGenie Search Debug")
    print("=" * 50)
    
    # Initialize services
    genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
    pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
    index = pc.Index('juspay-issues')
    
    # Check index stats
    print("\n📊 Pinecone Index Stats:")
    try:
        stats = index.describe_index_stats()
        print(f"  Total vectors: {stats.total_vector_count}")
        print(f"  Dimension: {stats.dimension}")
        print(f"  Index fullness: {stats.index_fullness}")
        
        if stats.total_vector_count == 0:
            print("❌ No vectors found in index! Need to train the model first.")
            return
            
    except Exception as e:
        print(f"❌ Error getting index stats: {e}")
        return
    
    # Test embedding generation
    print("\n🧠 Testing Embedding Generation:")
    query = "UPI payment failed with timeout"
    try:
        result = genai.embed_content(
            model='models/text-embedding-004',
            content=query,
            task_type='retrieval_query'
        )
        query_embedding = result['embedding']
        print(f"  ✅ Generated embedding for: '{query}'")
        print(f"  Embedding dimension: {len(query_embedding)}")
    except Exception as e:
        print(f"❌ Error generating embedding: {e}")
        return
    
    # Test vector search
    print("\n🔍 Testing Vector Search:")
    try:
        search_results = index.query(
            vector=query_embedding,
            top_k=5,
            include_metadata=True
        )
        
        print(f"  Found {len(search_results.matches)} matches")
        
        if search_results.matches:
            for i, match in enumerate(search_results.matches, 1):
                print(f"  {i}. ID: {match.id}")
                print(f"     Score: {match.score:.4f}")
                if match.metadata:
                    print(f"     Title: {match.metadata.get('title', 'N/A')}")
                print()
        else:
            print("  ❌ No matches found!")
            
    except Exception as e:
        print(f"❌ Error in vector search: {e}")
    
    # Test different queries
    test_queries = [
        "payment timeout",
        "UPI error",
        "webhook failed",
        "timeout issue"
    ]
    
    print("\n🧪 Testing Multiple Queries:")
    for test_query in test_queries:
        try:
            result = genai.embed_content(
                model='models/text-embedding-004',
                content=test_query,
                task_type='retrieval_query'
            )
            test_embedding = result['embedding']
            
            search_results = index.query(
                vector=test_embedding,
                top_k=3,
                include_metadata=True
            )
            
            print(f"  Query: '{test_query}' -> {len(search_results.matches)} matches")
            if search_results.matches:
                best_match = search_results.matches[0]
                print(f"    Best: {best_match.metadata.get('title', 'N/A')} (Score: {best_match.score:.3f})")
            
        except Exception as e:
            print(f"  ❌ Error with query '{test_query}': {e}")

if __name__ == "__main__":
    asyncio.run(debug_search())
