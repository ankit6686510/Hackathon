"""
Slack Message Extraction Service
Automatically extracts incident information from Slack #issues channel
"""

import os
import re
import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass

from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError

from app.services.ai_service import ai_service
from app.services.hybrid_search import hybrid_search_service


@dataclass
class ExtractedIncident:
    """Extracted incident data structure"""
    title: str
    description: str
    resolution: str = ""
    tags: List[str] = None
    status: str = "reported"
    reporter: str = ""
    channel: str = ""
    thread_ts: str = ""
    created_at: str = ""
    confidence: float = 0.0
    raw_messages: List[Dict] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.raw_messages is None:
            self.raw_messages = []


class SlackMessageExtractor:
    """
    Extracts incident information from Slack messages using AI
    """
    
    def __init__(self):
        self.client = AsyncWebClient(token=os.getenv("SLACK_BOT_TOKEN"))
        self.ai_service = ai_service
        self.hybrid_search = hybrid_search_service
        
        # Channel configuration
        self.issues_channel = "#issues"
        self.issues_channel_id = None
        
        # Extraction patterns
        self.incident_keywords = [
            "error", "failed", "failure", "timeout", "issue", "problem", 
            "broken", "not working", "crash", "exception", "bug", "down",
            "outage", "slow", "performance", "latency", "502", "500", "404",
            "payment", "gateway", "api", "database", "connection", "ssl",
            "webhook", "callback", "integration", "merchant", "transaction"
        ]
        
        # Resolution indicators
        self.resolution_keywords = [
            "fixed", "resolved", "solved", "working", "solution", "fix",
            "patched", "updated", "deployed", "corrected", "implemented"
        ]
    
    async def initialize(self):
        """Initialize the extractor and find channel ID"""
        try:
            # Get channel ID for #issues
            response = await self.client.conversations_list(types="public_channel")
            for channel in response["channels"]:
                if channel["name"] == "issues":
                    self.issues_channel_id = channel["id"]
                    break
            
            if not self.issues_channel_id:
                print(f"⚠️ Channel #issues not found. Please create it or invite the bot.")
                return False
            
            print(f"✅ Connected to #issues channel (ID: {self.issues_channel_id})")
            return True
            
        except SlackApiError as e:
            print(f"❌ Failed to initialize Slack extractor: {e}")
            return False
    
    async def extract_from_channel_history(self, hours_back: int = 24) -> List[ExtractedIncident]:
        """
        Extract incidents from recent channel history
        
        Args:
            hours_back: How many hours back to look for messages
            
        Returns:
            List of extracted incidents
        """
        if not self.issues_channel_id:
            await self.initialize()
            if not self.issues_channel_id:
                return []
        
        try:
            # Calculate timestamp for X hours ago
            oldest_ts = (datetime.now(timezone.utc).timestamp() - (hours_back * 3600))
            
            # Get channel messages
            response = await self.client.conversations_history(
                channel=self.issues_channel_id,
                oldest=str(oldest_ts),
                limit=100
            )
            
            messages = response["messages"]
            print(f"📥 Found {len(messages)} messages in last {hours_back} hours")
            
            # Group messages into potential incidents (threads)
            incident_threads = await self._group_messages_into_threads(messages)
            
            # Extract incidents from each thread
            extracted_incidents = []
            for thread in incident_threads:
                incident = await self._extract_incident_from_thread(thread)
                if incident and incident.confidence > 0.6:  # Only high-confidence extractions
                    extracted_incidents.append(incident)
            
            print(f"🎯 Extracted {len(extracted_incidents)} high-confidence incidents")
            return extracted_incidents
            
        except SlackApiError as e:
            print(f"❌ Failed to extract from channel history: {e}")
            return []
    
    async def _group_messages_into_threads(self, messages: List[Dict]) -> List[List[Dict]]:
        """
        Group messages into conversation threads
        
        Args:
            messages: List of Slack messages
            
        Returns:
            List of message threads
        """
        threads = {}
        standalone_messages = []
        
        for message in messages:
            # Skip bot messages and system messages
            if message.get("subtype") or message.get("bot_id"):
                continue
            
            thread_ts = message.get("thread_ts", message.get("ts"))
            
            if thread_ts not in threads:
                threads[thread_ts] = []
            
            threads[thread_ts].append(message)
        
        # Convert to list and sort by timestamp
        thread_list = []
        for thread_messages in threads.values():
            # Sort messages in thread by timestamp
            thread_messages.sort(key=lambda x: float(x["ts"]))
            thread_list.append(thread_messages)
        
        # Sort threads by first message timestamp
        thread_list.sort(key=lambda x: float(x[0]["ts"]), reverse=True)
        
        return thread_list
    
    async def _extract_incident_from_thread(self, thread_messages: List[Dict]) -> Optional[ExtractedIncident]:
        """
        Extract incident information from a message thread using AI
        
        Args:
            thread_messages: List of messages in the thread
            
        Returns:
            ExtractedIncident or None
        """
        if not thread_messages:
            return None
        
        # Combine all messages in thread
        combined_text = ""
        first_message = thread_messages[0]
        
        for msg in thread_messages:
            user_id = msg.get("user", "unknown")
            text = msg.get("text", "")
            timestamp = datetime.fromtimestamp(float(msg["ts"])).strftime("%H:%M")
            combined_text += f"[{timestamp}] <@{user_id}>: {text}\n"
        
        # Check if this looks like an incident
        if not self._looks_like_incident(combined_text):
            return None
        
        try:
            # Use AI to extract structured incident data
            extraction_prompt = f"""
You are an expert at extracting incident information from Slack conversations. 
Analyze this conversation and extract incident details if present.

CONVERSATION:
{combined_text}

Extract the following information and respond in JSON format:
{{
    "is_incident": true/false,
    "title": "Brief descriptive title of the issue",
    "description": "Detailed description of the problem",
    "resolution": "How it was fixed (if mentioned)",
    "tags": ["relevant", "technical", "tags"],
    "status": "reported/investigating/resolved",
    "confidence": 0.0-1.0,
    "reasoning": "Why you classified this as incident/not incident"
}}

RULES:
1. Only mark as incident if there's a clear technical problem
2. Title should be concise but descriptive (max 80 chars)
3. Description should capture the core issue
4. Tags should be technical keywords (payment, gateway, timeout, etc.)
5. Status: "reported" if just mentioned, "resolved" if fix is described
6. Confidence: How sure you are this is a real incident (0.0-1.0)
7. If not an incident (casual chat, questions, etc.), set is_incident: false
"""

            # Get AI extraction
            ai_response = await self.ai_service.generate_text(
                prompt=extraction_prompt,
                max_tokens=500,
                temperature=0.1
            )
            
            # Parse JSON response
            try:
                extracted_data = json.loads(ai_response.strip())
            except json.JSONDecodeError:
                # Try to extract JSON from response
                json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
                if json_match:
                    extracted_data = json.loads(json_match.group())
                else:
                    return None
            
            # Validate extraction
            if not extracted_data.get("is_incident", False):
                return None
            
            if extracted_data.get("confidence", 0) < 0.6:
                return None
            
            # Create ExtractedIncident
            incident = ExtractedIncident(
                title=extracted_data.get("title", "Unknown Issue"),
                description=extracted_data.get("description", ""),
                resolution=extracted_data.get("resolution", ""),
                tags=extracted_data.get("tags", []),
                status=extracted_data.get("status", "reported"),
                reporter=first_message.get("user", ""),
                channel="#issues",
                thread_ts=first_message.get("thread_ts", first_message.get("ts")),
                created_at=datetime.fromtimestamp(float(first_message["ts"])).isoformat(),
                confidence=extracted_data.get("confidence", 0.0),
                raw_messages=thread_messages
            )
            
            print(f"✅ Extracted incident: {incident.title} (confidence: {incident.confidence:.2f})")
            return incident
            
        except Exception as e:
            print(f"❌ Failed to extract incident from thread: {e}")
            return None
    
    def _looks_like_incident(self, text: str) -> bool:
        """
        Quick check if text looks like an incident report
        
        Args:
            text: Combined message text
            
        Returns:
            True if it looks like an incident
        """
        text_lower = text.lower()
        
        # Check for incident keywords
        incident_score = sum(1 for keyword in self.incident_keywords if keyword in text_lower)
        
        # Check for technical patterns
        technical_patterns = [
            r'\b\d{3}\b',  # HTTP status codes
            r'error\s+\d+',  # Error codes
            r'timeout',
            r'failed?',
            r'exception',
            r'stack\s+trace',
            r'api\s+call',
            r'database',
            r'connection',
            r'gateway'
        ]
        
        pattern_score = sum(1 for pattern in technical_patterns if re.search(pattern, text_lower))
        
        # Minimum threshold for considering as incident
        return (incident_score >= 2) or (pattern_score >= 2) or ("error" in text_lower and len(text) > 50)
    
    async def add_extracted_incidents_to_knowledge_base(self, incidents: List[ExtractedIncident]) -> int:
        """
        Add extracted incidents to the knowledge base
        
        Args:
            incidents: List of extracted incidents
            
        Returns:
            Number of incidents successfully added
        """
        if not incidents:
            return 0
        
        try:
            # Load existing issues
            issues_file = "issues.json"
            existing_issues = []
            
            if os.path.exists(issues_file):
                with open(issues_file, 'r') as f:
                    existing_issues = json.load(f)
            
            # Convert incidents to issue format
            new_issues = []
            for incident in incidents:
                # Generate unique ID
                incident_id = f"SLACK-{int(datetime.now().timestamp())}-{len(new_issues) + 1}"
                
                issue = {
                    "id": incident_id,
                    "title": incident.title,
                    "description": incident.description,
                    "resolution": incident.resolution or "Resolution pending - extracted from Slack discussion",
                    "tags": incident.tags,
                    "created_at": incident.created_at,
                    "resolved_by": f"slack-user-{incident.reporter}",
                    "source": "slack_extraction",
                    "channel": incident.channel,
                    "thread_ts": incident.thread_ts,
                    "confidence": incident.confidence,
                    "status": incident.status
                }
                
                new_issues.append(issue)
            
            # Add to existing issues
            all_issues = existing_issues + new_issues
            
            # Save updated issues
            with open(issues_file, 'w') as f:
                json.dump(all_issues, f, indent=2)
            
            # Rebuild search indices
            print("🔄 Rebuilding search indices with new incidents...")
            await self.hybrid_search.build_indices(all_issues)
            
            print(f"✅ Added {len(new_issues)} incidents to knowledge base")
            return len(new_issues)
            
        except Exception as e:
            print(f"❌ Failed to add incidents to knowledge base: {e}")
            return 0
    
    async def monitor_channel_continuously(self, check_interval: int = 300):
        """
        Continuously monitor #issues channel for new incidents
        
        Args:
            check_interval: How often to check for new messages (seconds)
        """
        print(f"🔄 Starting continuous monitoring of #issues channel (every {check_interval}s)")
        
        last_check_time = datetime.now(timezone.utc).timestamp()
        
        while True:
            try:
                # Extract incidents since last check
                hours_back = (check_interval / 3600) + 0.1  # Add small buffer
                incidents = await self.extract_from_channel_history(hours_back)
                
                if incidents:
                    # Add to knowledge base
                    added_count = await self.add_extracted_incidents_to_knowledge_base(incidents)
                    if added_count > 0:
                        print(f"🎯 Live learning: Added {added_count} new incidents from Slack!")
                
                last_check_time = datetime.now(timezone.utc).timestamp()
                
                # Wait before next check
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                print(f"❌ Error in continuous monitoring: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying


# Global instance
slack_extractor = SlackMessageExtractor()


async def extract_and_learn_from_slack(hours_back: int = 24) -> Dict[str, Any]:
    """
    One-time extraction from Slack #issues channel
    
    Args:
        hours_back: How many hours back to extract
        
    Returns:
        Extraction results
    """
    print(f"🚀 Starting Slack extraction from last {hours_back} hours...")
    
    # Initialize extractor
    if not await slack_extractor.initialize():
        return {"success": False, "error": "Failed to initialize Slack connection"}
    
    # Extract incidents
    incidents = await slack_extractor.extract_from_channel_history(hours_back)
    
    if not incidents:
        return {
            "success": True,
            "incidents_found": 0,
            "incidents_added": 0,
            "message": "No incidents found in the specified time period"
        }
    
    # Add to knowledge base
    added_count = await slack_extractor.add_extracted_incidents_to_knowledge_base(incidents)
    
    return {
        "success": True,
        "incidents_found": len(incidents),
        "incidents_added": added_count,
        "incidents": [
            {
                "title": inc.title,
                "confidence": inc.confidence,
                "status": inc.status,
                "tags": inc.tags
            }
            for inc in incidents
        ]
    }


async def start_continuous_monitoring():
    """Start continuous monitoring of Slack #issues channel"""
    if not await slack_extractor.initialize():
        print("❌ Cannot start monitoring - Slack connection failed")
        return
    
    await slack_extractor.monitor_channel_continuously(check_interval=300)  # Check every 5 minutes
