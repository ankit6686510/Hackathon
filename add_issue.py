#!/usr/bin/env python3
"""
Interactive script to add new issues to the training data
"""

import json
import os
from datetime import datetime
from pathlib import Path

def get_next_id(issues):
    """Get the next available issue ID"""
    if not issues:
        return "JSP-1001"
    
    # Extract all numeric IDs
    numeric_ids = []
    for issue in issues:
        if issue.get('id', '').startswith('JSP-'):
            try:
                num = int(issue['id'].split('-')[1])
                numeric_ids.append(num)
            except (ValueError, IndexError):
                continue
    
    if not numeric_ids:
        return "JSP-1001"
    
    next_num = max(numeric_ids) + 1
    return f"JSP-{next_num}"

def add_new_issue():
    """Interactive function to add a new issue"""
    
    # Read existing issues
    issues_file = Path("issues.json")
    if not issues_file.exists():
        print("❌ issues.json not found!")
        return
    
    with open(issues_file, 'r') as f:
        issues = json.load(f)
    
    print("🚀 Adding New Issue to Training Data")
    print("=" * 50)
    
    # Get issue details from user
    print("\n📝 Enter Issue Details:")
    
    # Auto-generate ID
    new_id = get_next_id(issues)
    print(f"   ID: {new_id} (auto-generated)")
    
    title = input("   Title: ").strip()
    if not title:
        print("❌ Title is required!")
        return
    
    print("\n📄 Description (enter multiple lines, end with 'END' on new line):")
    description_lines = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        description_lines.append(line)
    description = "\n".join(description_lines).strip()
    
    print("\n🔧 Resolution (enter multiple lines, end with 'END' on new line):")
    resolution_lines = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        resolution_lines.append(line)
    resolution = "\n".join(resolution_lines).strip()
    
    print("\n🏷️  Tags (comma-separated):")
    tags_input = input("   Tags: ").strip()
    tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()]
    
    print("\n👤 Resolved by:")
    resolved_by = input("   Email: ").strip()
    if not resolved_by:
        resolved_by = "unknown@juspay.in"
    
    # Create new issue
    new_issue = {
        "id": new_id,
        "title": title,
        "description": description,
        "resolution": resolution,
        "tags": tags,
        "created_at": datetime.now().strftime("%Y-%m-%d"),
        "resolved_by": resolved_by
    }
    
    # Add to issues list
    issues.append(new_issue)
    
    # Save back to file
    with open(issues_file, 'w') as f:
        json.dump(issues, f, indent=2)
    
    print(f"\n✅ Issue {new_id} added successfully!")
    print(f"📊 Total issues in dataset: {len(issues)}")
    
    # Show summary
    print(f"\n📋 Issue Summary:")
    print(f"   ID: {new_issue['id']}")
    print(f"   Title: {new_issue['title']}")
    print(f"   Tags: {', '.join(new_issue['tags'])}")
    print(f"   Description: {new_issue['description'][:100]}...")
    print(f"   Resolution: {new_issue['resolution'][:100]}...")
    
    return new_issue

def show_stats():
    """Show dataset statistics"""
    issues_file = Path("issues.json")
    if not issues_file.exists():
        print("❌ issues.json not found!")
        return
    
    with open(issues_file, 'r') as f:
        issues = json.load(f)
    
    print(f"📊 Dataset Statistics")
    print("=" * 30)
    print(f"   Total Issues: {len(issues)}")
    
    # Count by tags
    tag_counts = {}
    for issue in issues:
        for tag in issue.get('tags', []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    
    # Show top 10 tags
    top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    print(f"   Top Tags:")
    for tag, count in top_tags:
        print(f"     {tag}: {count}")
    
    # Show recent issues
    recent_issues = sorted(issues, key=lambda x: x.get('created_at', ''), reverse=True)[:5]
    print(f"\n   Recent Issues:")
    for issue in recent_issues:
        print(f"     {issue['id']}: {issue['title']}")
    
    print()

def main():
    """Main interactive menu"""
    while True:
        print("\n🎯 SherlockAI Training Data Manager")
        print("=" * 40)
        print("1. Add new issue")
        print("2. Show statistics")
        print("3. Exit")
        
        choice = input("\nSelect option (1-3): ").strip()
        
        if choice == "1":
            add_new_issue()
        elif choice == "2":
            show_stats()
        elif choice == "3":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please select 1, 2, or 3.")

if __name__ == "__main__":
    main()
