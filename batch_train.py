#!/usr/bin/env python3
"""
Batch training script to add multiple issues at once
"""

import json
from pathlib import Path

def add_issues_batch(issues_data):
    """Add multiple issues to the training data"""
    
    issues_file = Path("issues.json")
    
    # Read existing issues
    if issues_file.exists():
        with open(issues_file, 'r') as f:
            issues = json.load(f)
    else:
        issues = []
    
    # Add new issues
    for issue_data in issues_data:
        issues.append(issue_data)
    
    # Save back to file
    with open(issues_file, 'w') as f:
        json.dump(issues, f, indent=2)
    
    print(f"✅ Added {len(issues_data)} issues to training data")
    print(f"📊 Total issues: {len(issues)}")
    
    return issues

# Example usage
if __name__ == "__main__":
    # Example: Add a new issue
    new_issues = [
        {
            "id": "JSP-1022",
            "title": "Example Issue",
            "description": "This is an example issue description",
            "resolution": "This is how to resolve the issue",
            "tags": ["example", "test"],
            "created_at": "2024-09-11",
            "resolved_by": "example@juspay.in"
        }
    ]
    
    # Uncomment the line below to add the example issue
    # add_issues_batch(new_issues)
    
    print("📝 To add issues, modify the new_issues list and uncomment the last line")
