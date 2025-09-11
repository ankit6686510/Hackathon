#!/usr/bin/env python3
"""
SherlockAI Enterprise Data Ingestion
Industry-grade data ingestion for large-scale training from multiple sources
"""

import asyncio
import json
import csv
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime
import requests
from pathlib import Path
import os

# Set up environment
os.environ.setdefault('PYTHONPATH', '.')

from app.config import settings
from app.services.ai_service import ai_service
from app.database import get_database, init_database
from app.models import Issue
from train_model import SherlockAITrainer

class EnterpriseDataIngestion:
    """Enterprise-grade data ingestion for SherlockAI"""
    
    def __init__(self):
        self.trainer = SherlockAITrainer()
        self.ai_service = ai_service
    
    # ==================== JIRA INTEGRATION ====================
    
    async def ingest_from_jira(self, jira_url: str, username: str, api_token: str, 
                              project_key: str, max_issues: int = 1000) -> Dict[str, int]:
        """
        Ingest resolved issues from Jira
        
        Args:
            jira_url: Your Jira instance URL (e.g., "https://company.atlassian.net")
            username: Jira username/email
            api_token: Jira API token
            project_key: Jira project key (e.g., "JSP", "TECH")
            max_issues: Maximum number of issues to fetch
        """
        print(f"🔄 Ingesting from Jira: {jira_url}/projects/{project_key}")
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        auth = (username, api_token)
        
        # JQL to get resolved issues with descriptions and resolutions
        jql = f'project = "{project_key}" AND status = "Done" AND resolution != "Unresolved" ORDER BY created DESC'
        
        url = f"{jira_url}/rest/api/3/search"
        params = {
            "jql": jql,
            "maxResults": max_issues,
            "fields": "summary,description,resolution,created,assignee,labels,components"
        }
        
        try:
            response = requests.get(url, headers=headers, auth=auth, params=params)
            response.raise_for_status()
            
            data = response.json()
            issues = data.get("issues", [])
            
            print(f"✅ Found {len(issues)} resolved issues in Jira")
            
            stats = {"total": len(issues), "processed": 0, "success": 0}
            
            await init_database()
            
            for jira_issue in issues:
                try:
                    # Extract issue data
                    fields = jira_issue["fields"]
                    
                    issue_data = {
                        "id": f"JIRA-{jira_issue['key']}",
                        "title": fields.get("summary", ""),
                        "description": self._clean_jira_text(fields.get("description", "")),
                        "resolution": self._clean_jira_text(fields.get("resolution", {}).get("description", "")),
                        "tags": [label for label in fields.get("labels", [])] + 
                               [comp["name"] for comp in fields.get("components", [])],
                        "created_at": fields.get("created", "")[:10],  # Extract date part
                        "resolved_by": fields.get("assignee", {}).get("emailAddress", "unknown") if fields.get("assignee") else "unknown"
                    }
                    
                    # Skip if missing critical data
                    if not issue_data["title"] or not issue_data["description"]:
                        continue
                    
                    # Add to database and vector store
                    async for db in get_database():
                        db_success = await self.trainer.add_issue_to_database(db, issue_data)
                        break
                    
                    vector_success = await self.trainer.add_issue_to_vector_db(issue_data)
                    
                    if db_success or vector_success:  # Success if added to either
                        stats["success"] += 1
                    
                    stats["processed"] += 1
                    
                    if stats["processed"] % 10 == 0:
                        print(f"📊 Processed {stats['processed']}/{stats['total']} issues...")
                
                except Exception as e:
                    print(f"⚠️  Error processing issue {jira_issue.get('key', 'unknown')}: {e}")
                    continue
            
            print(f"🎉 Jira ingestion completed: {stats['success']}/{stats['total']} issues added")
            return stats
            
        except requests.RequestException as e:
            print(f"❌ Error connecting to Jira: {e}")
            return {"total": 0, "processed": 0, "success": 0}
    
    # ==================== CSV/EXCEL INGESTION ====================
    
    async def ingest_from_csv(self, csv_file: str, mapping: Dict[str, str] = None) -> Dict[str, int]:
        """
        Ingest issues from CSV file
        
        Args:
            csv_file: Path to CSV file
            mapping: Column mapping {"csv_column": "issue_field"}
                    Default: {"title": "title", "description": "description", "resolution": "resolution"}
        """
        print(f"🔄 Ingesting from CSV: {csv_file}")
        
        # Default column mapping
        default_mapping = {
            "title": "title",
            "description": "description", 
            "resolution": "resolution",
            "tags": "tags",
            "created_at": "created_at",
            "resolved_by": "resolved_by",
            "id": "id"
        }
        
        if mapping:
            default_mapping.update(mapping)
        
        try:
            # Read CSV
            df = pd.read_csv(csv_file)
            print(f"✅ Loaded {len(df)} rows from CSV")
            
            stats = {"total": len(df), "processed": 0, "success": 0}
            
            await init_database()
            
            for index, row in df.iterrows():
                try:
                    # Map CSV columns to issue fields
                    issue_data = {}
                    
                    for issue_field, csv_column in default_mapping.items():
                        if csv_column in row and pd.notna(row[csv_column]):
                            value = row[csv_column]
                            
                            # Handle tags (convert string to list)
                            if issue_field == "tags" and isinstance(value, str):
                                value = [tag.strip() for tag in value.split(",")]
                            
                            issue_data[issue_field] = value
                    
                    # Generate ID if not provided
                    if "id" not in issue_data:
                        issue_data["id"] = f"CSV-{index + 1:04d}"
                    
                    # Set defaults
                    issue_data.setdefault("created_at", datetime.now().strftime("%Y-%m-%d"))
                    issue_data.setdefault("resolved_by", "csv-import")
                    issue_data.setdefault("tags", [])
                    
                    # Skip if missing critical data
                    if not issue_data.get("title") or not issue_data.get("description"):
                        continue
                    
                    # Add to database and vector store
                    async for db in get_database():
                        db_success = await self.trainer.add_issue_to_database(db, issue_data)
                        break
                    
                    vector_success = await self.trainer.add_issue_to_vector_db(issue_data)
                    
                    if db_success or vector_success:
                        stats["success"] += 1
                    
                    stats["processed"] += 1
                    
                    if stats["processed"] % 50 == 0:
                        print(f"📊 Processed {stats['processed']}/{stats['total']} rows...")
                
                except Exception as e:
                    print(f"⚠️  Error processing row {index}: {e}")
                    continue
            
            print(f"🎉 CSV ingestion completed: {stats['success']}/{stats['total']} issues added")
            return stats
            
        except Exception as e:
            print(f"❌ Error reading CSV file: {e}")
            return {"total": 0, "processed": 0, "success": 0}
    
    # ==================== ZENDESK INTEGRATION ====================
    
    async def ingest_from_zendesk(self, subdomain: str, email: str, api_token: str, 
                                 max_tickets: int = 1000) -> Dict[str, int]:
        """
        Ingest resolved tickets from Zendesk
        
        Args:
            subdomain: Zendesk subdomain (e.g., "company" for company.zendesk.com)
            email: Zendesk admin email
            api_token: Zendesk API token
            max_tickets: Maximum number of tickets to fetch
        """
        print(f"🔄 Ingesting from Zendesk: {subdomain}.zendesk.com")
        
        base_url = f"https://{subdomain}.zendesk.com/api/v2"
        auth = (f"{email}/token", api_token)
        
        # Get solved tickets
        url = f"{base_url}/tickets.json"
        params = {
            "status": "solved",
            "per_page": min(max_tickets, 100),  # Zendesk max per page
            "sort_by": "created_at",
            "sort_order": "desc"
        }
        
        try:
            all_tickets = []
            
            while len(all_tickets) < max_tickets:
                response = requests.get(url, auth=auth, params=params)
                response.raise_for_status()
                
                data = response.json()
                tickets = data.get("tickets", [])
                
                if not tickets:
                    break
                
                all_tickets.extend(tickets)
                
                # Check for next page
                if not data.get("next_page"):
                    break
                
                url = data["next_page"]
                params = {}  # Next page URL already has params
                
                print(f"📊 Fetched {len(all_tickets)} tickets so far...")
            
            print(f"✅ Found {len(all_tickets)} solved tickets in Zendesk")
            
            stats = {"total": len(all_tickets), "processed": 0, "success": 0}
            
            await init_database()
            
            for ticket in all_tickets:
                try:
                    # Get ticket comments for resolution
                    comments_url = f"{base_url}/tickets/{ticket['id']}/comments.json"
                    comments_response = requests.get(comments_url, auth=auth)
                    comments_data = comments_response.json()
                    
                    # Find resolution (usually the last public comment)
                    resolution = ""
                    for comment in reversed(comments_data.get("comments", [])):
                        if comment.get("public") and comment.get("body"):
                            resolution = comment["body"]
                            break
                    
                    issue_data = {
                        "id": f"ZD-{ticket['id']}",
                        "title": ticket.get("subject", ""),
                        "description": ticket.get("description", ""),
                        "resolution": self._clean_zendesk_text(resolution),
                        "tags": ticket.get("tags", []),
                        "created_at": ticket.get("created_at", "")[:10],
                        "resolved_by": "zendesk-agent"
                    }
                    
                    # Skip if missing critical data
                    if not issue_data["title"] or not issue_data["description"]:
                        continue
                    
                    # Add to database and vector store
                    async for db in get_database():
                        db_success = await self.trainer.add_issue_to_database(db, issue_data)
                        break
                    
                    vector_success = await self.trainer.add_issue_to_vector_db(issue_data)
                    
                    if db_success or vector_success:
                        stats["success"] += 1
                    
                    stats["processed"] += 1
                    
                    if stats["processed"] % 25 == 0:
                        print(f"📊 Processed {stats['processed']}/{stats['total']} tickets...")
                
                except Exception as e:
                    print(f"⚠️  Error processing ticket {ticket.get('id', 'unknown')}: {e}")
                    continue
            
            print(f"🎉 Zendesk ingestion completed: {stats['success']}/{stats['total']} tickets added")
            return stats
            
        except requests.RequestException as e:
            print(f"❌ Error connecting to Zendesk: {e}")
            return {"total": 0, "processed": 0, "success": 0}
    
    # ==================== SLACK EXPORT INGESTION ====================
    
    async def ingest_from_slack_export(self, export_dir: str, channels: List[str] = None) -> Dict[str, int]:
        """
        Ingest issues from Slack export data
        
        Args:
            export_dir: Path to Slack export directory
            channels: List of channel names to process (e.g., ["tech-support", "incidents"])
        """
        print(f"🔄 Ingesting from Slack export: {export_dir}")
        
        export_path = Path(export_dir)
        if not export_path.exists():
            print(f"❌ Export directory not found: {export_dir}")
            return {"total": 0, "processed": 0, "success": 0}
        
        # Get channels to process
        if not channels:
            channels = [d.name for d in export_path.iterdir() if d.is_dir()]
        
        stats = {"total": 0, "processed": 0, "success": 0}
        
        await init_database()
        
        for channel in channels:
            channel_path = export_path / channel
            if not channel_path.exists():
                continue
            
            print(f"📂 Processing channel: {channel}")
            
            # Process all JSON files in channel directory
            for json_file in channel_path.glob("*.json"):
                try:
                    with open(json_file, 'r') as f:
                        messages = json.load(f)
                    
                    # Look for thread conversations that look like issue resolutions
                    threads = self._extract_slack_threads(messages)
                    
                    for thread in threads:
                        if self._is_issue_thread(thread):
                            issue_data = self._convert_slack_thread_to_issue(thread, channel)
                            
                            if issue_data:
                                # Add to database and vector store
                                async for db in get_database():
                                    db_success = await self.trainer.add_issue_to_database(db, issue_data)
                                    break
                                
                                vector_success = await self.trainer.add_issue_to_vector_db(issue_data)
                                
                                if db_success or vector_success:
                                    stats["success"] += 1
                                
                                stats["total"] += 1
                
                except Exception as e:
                    print(f"⚠️  Error processing {json_file}: {e}")
                    continue
        
        print(f"🎉 Slack ingestion completed: {stats['success']}/{stats['total']} issues extracted")
        return stats
    
    # ==================== DATABASE MIGRATION ====================
    
    async def ingest_from_database(self, connection_string: str, query: str, 
                                  field_mapping: Dict[str, str]) -> Dict[str, int]:
        """
        Ingest issues from external database
        
        Args:
            connection_string: Database connection string
            query: SQL query to fetch issues
            field_mapping: Mapping of database columns to issue fields
        """
        print(f"🔄 Ingesting from external database")
        
        try:
            import sqlalchemy as sa
            
            engine = sa.create_engine(connection_string)
            
            with engine.connect() as conn:
                result = conn.execute(sa.text(query))
                rows = result.fetchall()
                columns = result.keys()
            
            print(f"✅ Fetched {len(rows)} rows from database")
            
            stats = {"total": len(rows), "processed": 0, "success": 0}
            
            await init_database()
            
            for row in rows:
                try:
                    # Convert row to dict
                    row_dict = dict(zip(columns, row))
                    
                    # Map database fields to issue fields
                    issue_data = {}
                    for issue_field, db_field in field_mapping.items():
                        if db_field in row_dict and row_dict[db_field] is not None:
                            issue_data[issue_field] = str(row_dict[db_field])
                    
                    # Set defaults
                    issue_data.setdefault("id", f"DB-{stats['processed'] + 1:04d}")
                    issue_data.setdefault("created_at", datetime.now().strftime("%Y-%m-%d"))
                    issue_data.setdefault("resolved_by", "db-import")
                    issue_data.setdefault("tags", [])
                    
                    # Skip if missing critical data
                    if not issue_data.get("title") or not issue_data.get("description"):
                        continue
                    
                    # Add to database and vector store
                    async for db in get_database():
                        db_success = await self.trainer.add_issue_to_database(db, issue_data)
                        break
                    
                    vector_success = await self.trainer.add_issue_to_vector_db(issue_data)
                    
                    if db_success or vector_success:
                        stats["success"] += 1
                    
                    stats["processed"] += 1
                    
                    if stats["processed"] % 100 == 0:
                        print(f"📊 Processed {stats['processed']}/{stats['total']} rows...")
                
                except Exception as e:
                    print(f"⚠️  Error processing row {stats['processed']}: {e}")
                    continue
            
            print(f"🎉 Database ingestion completed: {stats['success']}/{stats['total']} issues added")
            return stats
            
        except Exception as e:
            print(f"❌ Error connecting to database: {e}")
            return {"total": 0, "processed": 0, "success": 0}
    
    # ==================== UTILITY METHODS ====================
    
    def _clean_jira_text(self, text: str) -> str:
        """Clean Jira markup from text"""
        if not text:
            return ""
        
        # Remove common Jira markup
        import re
        
        # Remove code blocks
        text = re.sub(r'\{code[^}]*\}.*?\{code\}', '', text, flags=re.DOTALL)
        
        # Remove links
        text = re.sub(r'\[([^\]]+)\|[^\]]+\]', r'\1', text)
        
        # Remove other markup
        text = re.sub(r'[{}]', '', text)
        
        return text.strip()
    
    def _clean_zendesk_text(self, text: str) -> str:
        """Clean Zendesk HTML from text"""
        if not text:
            return ""
        
        import re
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Decode HTML entities
        import html
        text = html.unescape(text)
        
        return text.strip()
    
    def _extract_slack_threads(self, messages: List[Dict]) -> List[List[Dict]]:
        """Extract threaded conversations from Slack messages"""
        threads = {}
        
        for message in messages:
            if message.get("thread_ts"):
                thread_id = message["thread_ts"]
                if thread_id not in threads:
                    threads[thread_id] = []
                threads[thread_id].append(message)
            elif message.get("replies"):
                # This is a parent message with replies
                thread_id = message["ts"]
                if thread_id not in threads:
                    threads[thread_id] = []
                threads[thread_id].append(message)
        
        return list(threads.values())
    
    def _is_issue_thread(self, thread: List[Dict]) -> bool:
        """Determine if a Slack thread represents an issue resolution"""
        if len(thread) < 2:
            return False
        
        # Look for keywords that indicate issue resolution
        issue_keywords = ["error", "issue", "problem", "bug", "failed", "timeout", "exception"]
        resolution_keywords = ["fixed", "resolved", "solution", "workaround", "solved"]
        
        thread_text = " ".join([msg.get("text", "") for msg in thread]).lower()
        
        has_issue = any(keyword in thread_text for keyword in issue_keywords)
        has_resolution = any(keyword in thread_text for keyword in resolution_keywords)
        
        return has_issue and has_resolution
    
    def _convert_slack_thread_to_issue(self, thread: List[Dict], channel: str) -> Optional[Dict[str, Any]]:
        """Convert a Slack thread to an issue format"""
        if not thread:
            return None
        
        # First message is usually the issue description
        first_msg = thread[0]
        
        # Last few messages might contain the resolution
        resolution_msgs = thread[-3:] if len(thread) > 3 else thread[1:]
        
        issue_data = {
            "id": f"SLACK-{channel}-{first_msg.get('ts', '')}",
            "title": f"Issue from #{channel}: {first_msg.get('text', '')[:100]}...",
            "description": first_msg.get("text", ""),
            "resolution": " ".join([msg.get("text", "") for msg in resolution_msgs]),
            "tags": ["slack", channel],
            "created_at": datetime.fromtimestamp(float(first_msg.get("ts", 0))).strftime("%Y-%m-%d"),
            "resolved_by": "slack-team"
        }
        
        return issue_data

# ==================== USAGE EXAMPLES ====================

async def example_jira_ingestion():
    """Example: Ingest from Jira"""
    ingester = EnterpriseDataIngestion()
    
    stats = await ingester.ingest_from_jira(
        jira_url="https://yourcompany.atlassian.net",
        username="your-email@company.com",
        api_token="your-jira-api-token",
        project_key="JSP",
        max_issues=500
    )
    
    print(f"Jira ingestion stats: {stats}")

async def example_csv_ingestion():
    """Example: Ingest from CSV"""
    ingester = EnterpriseDataIngestion()
    
    # Custom column mapping
    mapping = {
        "title": "Issue Title",
        "description": "Problem Description", 
        "resolution": "Solution",
        "tags": "Categories",
        "resolved_by": "Engineer"
    }
    
    stats = await ingester.ingest_from_csv("issues_export.csv", mapping)
    print(f"CSV ingestion stats: {stats}")

async def example_zendesk_ingestion():
    """Example: Ingest from Zendesk"""
    ingester = EnterpriseDataIngestion()
    
    stats = await ingester.ingest_from_zendesk(
        subdomain="yourcompany",
        email="admin@company.com",
        api_token="your-zendesk-token",
        max_tickets=1000
    )
    
    print(f"Zendesk ingestion stats: {stats}")

if __name__ == "__main__":
    print("🚀 SherlockAI Enterprise Data Ingestion")
    print("=" * 50)
    print("Available ingestion methods:")
    print("1. Jira - ingest_from_jira()")
    print("2. CSV/Excel - ingest_from_csv()")
    print("3. Zendesk - ingest_from_zendesk()")
    print("4. Slack Export - ingest_from_slack_export()")
    print("5. Database - ingest_from_database()")
    print("\nSee example functions for usage details.")
