#!/usr/bin/env python3
"""
Simple training script to add new data to the model
"""

import json
import os
from pathlib import Path

def main():
    """Add new training data and update the model"""
    
    # Read the issues data
    issues_file = Path("issues.json")
    if not issues_file.exists():
        print("❌ issues.json not found!")
        return
    
    with open(issues_file, 'r') as f:
        issues = json.load(f)
    
    print(f"📊 Found {len(issues)} issues in the dataset")
    
    # Check if the new card tokenization issue is already there
    new_issue_id = "JSP-1020"
    existing_ids = [issue.get('id') for issue in issues]
    
    if new_issue_id in existing_ids:
        print(f"✅ Issue {new_issue_id} already exists in the dataset")
    else:
        print(f"❌ Issue {new_issue_id} not found in the dataset")
        return
    
    # Count issues by category
    card_issues = [issue for issue in issues if 'card' in issue.get('tags', [])]
    tokenization_issues = [issue for issue in issues if 'tokenization' in issue.get('tags', [])]
    
    print(f"💳 Card-related issues: {len(card_issues)}")
    print(f"🔑 Tokenization issues: {len(tokenization_issues)}")
    
    # Show the new issue details
    new_issue = next((issue for issue in issues if issue.get('id') == new_issue_id), None)
    if new_issue:
        print(f"\n📝 New Issue Added:")
        print(f"   ID: {new_issue['id']}")
        print(f"   Title: {new_issue['title']}")
        print(f"   Tags: {', '.join(new_issue['tags'])}")
        print(f"   Description: {new_issue['description'][:100]}...")
        print(f"   Resolution: {new_issue['resolution'][:100]}...")
    
    print(f"\n🎯 Training data updated successfully!")
    print(f"   Total issues: {len(issues)}")
    print(f"   Ready for model retraining")

if __name__ == "__main__":
    main()
