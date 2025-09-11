#!/usr/bin/env python3
"""
SherlockAI Model Training Script
This script loads issues into the vector database and provides utilities for training the model.
"""

import json
import asyncio
import os
from typing import List, Dict, Any
from datetime import datetime

# Set up environment
os.environ.setdefault('PYTHONPATH', '.')

from app.config import settings
from app.services.ai_service import ai_service
from app.database import get_database, init_database
from app.models import Issue, IssueCreate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

class SherlockAITrainer:
    """Training utilities for SherlockAI"""
    
    def __init__(self):
        self.ai_service = ai_service
        
    async def load_issues_from_json(self, json_file: str = "issues.json") -> List[Dict[str, Any]]:
        """Load issues from JSON file"""
        try:
            with open(json_file, 'r') as f:
                issues = json.load(f)
            print(f"✅ Loaded {len(issues)} issues from {json_file}")
            return issues
        except FileNotFoundError:
            print(f"❌ File {json_file} not found")
            return []
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing JSON: {e}")
            return []
    
    async def add_issue_to_database(self, db: AsyncSession, issue_data: Dict[str, Any]) -> bool:
        """Add a single issue to the database"""
        try:
            # Check if issue already exists
            result = await db.execute(select(Issue).where(Issue.id == issue_data["id"]))
            existing_issue = result.scalar_one_or_none()
            
            if existing_issue:
                print(f"⚠️  Issue {issue_data['id']} already exists in database")
                return False
            
            # Create new issue
            issue = Issue(
                id=issue_data["id"],
                title=issue_data["title"],
                description=issue_data["description"],
                resolution=issue_data.get("resolution", ""),
                status="resolved",
                tags=issue_data.get("tags", []),
                created_at=datetime.fromisoformat(issue_data.get("created_at", "2024-01-01")),
                resolved_by=issue_data.get("resolved_by", "system"),
                priority="medium",
                category="technical"
            )
            
            db.add(issue)
            await db.commit()
            print(f"✅ Added issue {issue_data['id']} to database")
            return True
            
        except Exception as e:
            print(f"❌ Error adding issue {issue_data.get('id', 'unknown')}: {e}")
            await db.rollback()
            return False
    
    async def add_issue_to_vector_db(self, issue_data: Dict[str, Any]) -> bool:
        """Add a single issue to the vector database"""
        try:
            # Create combined text for embedding
            combined_text = f"{issue_data['title']}. {issue_data['description']}. Resolution: {issue_data.get('resolution', '')}"
            
            # Generate embedding
            embedding = await self.ai_service.embed_text(combined_text, use_cache=False)
            
            # Prepare metadata
            metadata = {
                "id": issue_data["id"],
                "title": issue_data["title"],
                "description": issue_data["description"],
                "resolution": issue_data.get("resolution", ""),
                "tags": issue_data.get("tags", []),
                "created_at": issue_data.get("created_at", "2024-01-01"),
                "resolved_by": issue_data.get("resolved_by", "system")
            }
            
            # Store in Pinecone
            await self.ai_service.store_embedding(issue_data["id"], embedding, metadata)
            print(f"✅ Added issue {issue_data['id']} to vector database")
            return True
            
        except Exception as e:
            print(f"❌ Error adding issue {issue_data.get('id', 'unknown')} to vector DB: {e}")
            return False
    
    async def train_from_json(self, json_file: str = "issues.json") -> Dict[str, int]:
        """Train the model by loading issues from JSON file"""
        print(f"🚀 Starting training from {json_file}...")
        
        # Initialize database
        await init_database()
        
        # Load issues
        issues = await self.load_issues_from_json(json_file)
        if not issues:
            return {"total": 0, "database_added": 0, "vector_added": 0}
        
        stats = {"total": len(issues), "database_added": 0, "vector_added": 0}
        
        # Get database session
        async for db in get_database():
            for issue in issues:
                # Add to database
                if await self.add_issue_to_database(db, issue):
                    stats["database_added"] += 1
                
                # Add to vector database
                if await self.add_issue_to_vector_db(issue):
                    stats["vector_added"] += 1
            
            break  # Exit the async generator
        
        print(f"\n🎉 Training completed!")
        print(f"📊 Stats: {stats['database_added']}/{stats['total']} added to database, {stats['vector_added']}/{stats['total']} added to vector DB")
        return stats
    
    async def add_single_issue(self, title: str, description: str, resolution: str, 
                             tags: List[str] = None, resolved_by: str = "manual") -> bool:
        """Add a single issue manually"""
        # Generate unique ID
        issue_id = f"MANUAL-{int(datetime.now().timestamp())}"
        
        issue_data = {
            "id": issue_id,
            "title": title,
            "description": description,
            "resolution": resolution,
            "tags": tags or [],
            "created_at": datetime.now().isoformat(),
            "resolved_by": resolved_by
        }
        
        print(f"🔄 Adding manual issue: {title}")
        
        # Initialize database
        await init_database()
        
        # Add to database
        async for db in get_database():
            db_success = await self.add_issue_to_database(db, issue_data)
            break
        
        # Add to vector database
        vector_success = await self.add_issue_to_vector_db(issue_data)
        
        if db_success and vector_success:
            print(f"✅ Successfully added issue: {issue_id}")
            return True
        else:
            print(f"❌ Failed to add issue: {issue_id}")
            return False
    
    async def get_vector_db_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector database"""
        try:
            stats = await self.ai_service.get_index_stats()
            return stats
        except Exception as e:
            print(f"❌ Error getting vector DB stats: {e}")
            return {}
    
    async def test_search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Test search functionality"""
        print(f"🔍 Testing search for: '{query}'")
        
        try:
            # Generate embedding for query
            query_embedding = await self.ai_service.embed_text(query)
            
            # Search vector database
            results = await self.ai_service.search_similar(query_embedding, top_k=top_k)
            
            print(f"📊 Found {len(results)} results:")
            for i, result in enumerate(results, 1):
                print(f"  {i}. {result.get('title', 'No title')} (Score: {result.get('score', 0):.3f})")
            
            return results
            
        except Exception as e:
            print(f"❌ Error testing search: {e}")
            return []

async def main():
    """Main training function"""
    trainer = SherlockAITrainer()
    
    print("🔧 SherlockAI Model Trainer")
    print("=" * 50)
    
    # Check current vector DB stats
    print("\n📊 Current Vector Database Stats:")
    stats = await trainer.get_vector_db_stats()
    if stats:
        print(f"  Total vectors: {stats.get('total_vectors', 0)}")
        print(f"  Dimension: {stats.get('dimension', 'unknown')}")
    
    # Train from JSON
    print("\n🚀 Training from issues.json...")
    training_stats = await trainer.train_from_json()
    
    # Test search
    print("\n🔍 Testing search functionality...")
    await trainer.test_search("UPI payment failed")
    await trainer.test_search("timeout error")
    await trainer.test_search("webhook issues")
    
    print("\n✅ Training completed! Your SherlockAI model is now ready to use.")
    print("\n💡 To add new issues, you can:")
    print("   1. Add them to issues.json and run this script again")
    print("   2. Use the add_single_issue() function")
    print("   3. Use the web interface (coming soon)")

if __name__ == "__main__":
    asyncio.run(main())
