#!/usr/bin/env python3
"""
Build hybrid search indices from issues.json
"""

import asyncio
import json
import sys
import os
from pathlib import Path

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

from app.services.hybrid_search import hybrid_search_service

async def build_indices():
    """Build hybrid search indices from issues.json"""
    
    print("🔧 Building Hybrid Search Indices")
    print("=" * 50)
    
    # Load issues from JSON file
    issues_file = Path("issues.json")
    if not issues_file.exists():
        print("❌ issues.json not found!")
        return False
    
    try:
        with open(issues_file, 'r') as f:
            issues = json.load(f)
        
        print(f"📊 Loaded {len(issues)} issues from issues.json")
        
        # Build indices
        print("🔨 Building BM25 and TF-IDF indices...")
        success = await hybrid_search_service.build_indices(issues)
        
        if success:
            print("✅ Hybrid search indices built successfully!")
            
            # Show statistics
            stats = hybrid_search_service.get_index_stats()
            print("\n📈 Index Statistics:")
            print(f"  • Corpus Size: {stats['corpus_size']} documents")
            print(f"  • BM25 Available: {stats['bm25_available']}")
            print(f"  • TF-IDF Available: {stats['tfidf_available']}")
            
            if stats['bm25_available']:
                print(f"  • BM25 Vocabulary: {stats['bm25_vocab_size']} terms")
            
            if stats['tfidf_available']:
                print(f"  • TF-IDF Features: {stats['tfidf_features']} features")
                print(f"  • TF-IDF Documents: {stats['tfidf_documents']} documents")
            
            print(f"\n💾 Cache Files:")
            for cache_type, exists in stats['cache_files_exist'].items():
                status = "✅" if exists else "❌"
                print(f"  • {cache_type.upper()}: {status}")
            
            return True
        else:
            print("❌ Failed to build hybrid search indices")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def test_hybrid_search():
    """Test the hybrid search functionality"""
    
    print("\n🧪 Testing Hybrid Search")
    print("=" * 30)
    
    test_queries = [
        "UPI payment failed",
        "gateway timeout error",
        "snapdeal pinelabs integration",
        "refund processing issue",
        "webhook delivery failure"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Query: '{query}'")
        
        try:
            results = await hybrid_search_service.hybrid_search(query, top_k=3)
            
            if results:
                print(f"  Found {len(results)} results:")
                for i, result in enumerate(results, 1):
                    print(f"    {i}. {result['id']} - {result['title'][:50]}...")
                    print(f"       Fused Score: {result['fused_score']:.3f}")
                    print(f"       Methods: {', '.join(result['search_methods'])}")
                    print(f"       Semantic: {result['semantic_score']:.3f}, "
                          f"BM25: {result['bm25_score']:.3f}, "
                          f"TF-IDF: {result['tfidf_score']:.3f}")
            else:
                print("  No results found")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")

if __name__ == "__main__":
    async def main():
        # Build indices
        success = await build_indices()
        
        if success:
            # Test search
            await test_hybrid_search()
            print("\n🎉 Hybrid search system is ready!")
        else:
            print("\n❌ Failed to set up hybrid search system")
    
    asyncio.run(main())
