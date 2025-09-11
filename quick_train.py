#!/usr/bin/env python3
"""
Quick training script to add new issues to the vector database
"""

import json
import asyncio
import os
from pathlib import Path

# Set up environment
os.environ.setdefault('PYTHONPATH', '.')

async def quick_train():
    """Quick training without full dependencies"""
    
    print("🚀 Quick Training - Adding New Issues to Vector Database")
    print("=" * 60)
    
    # Read issues from JSON
    issues_file = Path("issues.json")
    if not issues_file.exists():
        print("❌ issues.json not found!")
        return
    
    with open(issues_file, 'r') as f:
        issues = json.load(f)
    
    print(f"📊 Found {len(issues)} issues in the dataset")
    
    # Show recent issues that might be new
    recent_issues = [issue for issue in issues if issue.get('id', '').startswith('JSP-102')]
    print(f"\n🆕 Recent issues (JSP-102x): {len(recent_issues)}")
    for issue in recent_issues:
        print(f"   {issue['id']}: {issue['title']}")
    
    print(f"\n✅ Training data is ready!")
    print(f"📝 To actually train the model, you need to:")
    print(f"   1. Set up your API keys in .env file")
    print(f"   2. Run: python3 train_model.py")
    print(f"   3. Or start the backend server to use the data")
    
    # Show what the model would learn from
    print(f"\n🎯 The model will learn from these categories:")
    tag_counts = {}
    for issue in issues:
        for tag in issue.get('tags', []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    
    top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    for tag, count in top_tags:
        print(f"   {tag}: {count} issues")

if __name__ == "__main__":
    asyncio.run(quick_train())
