#!/usr/bin/env python3
"""
SherlockAI Slack Integration
Real-time Slack bot for querying SherlockAI directly from Slack channels
"""

import os
import asyncio
import json
from typing import Dict, Any, Optional
from datetime import datetime

# Slack SDK
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_sdk.web.async_client import AsyncWebClient

# Set up environment
os.environ.setdefault('PYTHONPATH', '.')

from app.services.ai_service import ai_service
from app.database import get_database, init_database
from app.models import Issue
from sqlalchemy import select

class SherlockAISlackBot:
    """Slack bot for SherlockAI integration"""
    
    def __init__(self):
        # Initialize Slack app
        self.app = AsyncApp(
            token=os.getenv("SLACK_BOT_TOKEN"),
            signing_secret=os.getenv("SLACK_SIGNING_SECRET")
        )
        
        # Initialize AI service
        self.ai_service = ai_service
        
        # Set up event handlers
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Set up Slack event handlers"""
        
        # Slash command handler
        @self.app.command("/sherlock")
        async def handle_sherlock_command(ack, respond, command):
            await ack()
            await self._handle_search_query(respond, command)
        
        # Alternative slash command
        @self.app.command("/SherlockAI")
        async def handle_SherlockAI_command(ack, respond, command):
            await ack()
            await self._handle_search_query(respond, command)
        
        # App mention handler (when @SherlockAI is mentioned)
        @self.app.event("app_mention")
        async def handle_app_mention(event, say):
            await self._handle_mention(say, event)
        
        # Direct message handler
        @self.app.event("message")
        async def handle_direct_message(event, say):
            # Only respond to direct messages (not channel messages)
            if event.get("channel_type") == "im":
                await self._handle_direct_message(say, event)
    
    async def _handle_search_query(self, respond, command):
        """Handle slash command queries"""
        query = command.get("text", "").strip()
        user_id = command.get("user_id")
        channel_id = command.get("channel_id")
        
        if not query:
            await respond({
                "response_type": "ephemeral",
                "text": "🔍 *SherlockAI - Your Advanced AI Assistant*\n\n"
                       "Use `/sherlock <any question>` to get help with ANYTHING!\n\n"
                       "*Examples:*\n"
                       "• `/sherlock payment timeout error` (Technical issues)\n"
                       "• `/sherlock how to implement OAuth in Python` (Code help)\n"
                       "• `/sherlock explain machine learning basics` (Learning)\n"
                       "• `/sherlock can you help with slack integration` (General questions)\n"
                       "• `/sherlock write a function to sort arrays` (Code generation)"
            })
            return
        
        # Show loading message
        await respond({
            "response_type": "ephemeral",
            "text": f"🤖 Processing your request: *{query}*\n⏳ Please wait..."
        })
        
        try:
            # Use the new smart response system
            smart_response = await self.ai_service.generate_smart_response(query)
            
            if smart_response["type"] == "historical_issues":
                # Format historical issues like before
                response = await self._format_search_results(query, smart_response["content"], user_id)
                await respond({
                    "response_type": "in_channel",  # Make it visible to everyone
                    "blocks": response
                })
            else:
                # Handle all other response types (conversational, code, general)
                await respond({
                    "response_type": "in_channel",
                    "text": f"🤖 *SherlockAI Response for <@{user_id}>:*\n\n{smart_response['content']}"
                })
                
        except Exception as e:
            await respond({
                "response_type": "ephemeral",
                "text": f"❌ I apologize, but I'm experiencing a technical issue right now. Please try again in a moment, and I'll be happy to help you with your question!"
            })
    
    async def _handle_mention(self, say, event):
        """Handle @SherlockAI mentions in channels"""
        text = event.get("text", "")
        user_id = event.get("user")
        
        # Extract query (remove the mention)
        query = text.split(">", 1)[-1].strip() if ">" in text else text.strip()
        
        if not query or query.lower() in ["help", "hi", "hello"]:
            await say({
                "text": f"👋 Hi <@{user_id}>! I'm SherlockAI, your advanced AI assistant!\n\n"
                       "*I can help you with ANYTHING:*\n"
                       "• Technical issues and debugging\n"
                       "• Code generation and programming\n"
                       "• General questions and explanations\n"
                       "• Creative tasks and brainstorming\n\n"
                       "*Just mention me with any question:*\n"
                       "`@SherlockAI How do I implement OAuth in Python?`\n"
                       "`@SherlockAI Explain machine learning basics`\n"
                       "`@SherlockAI Help with payment API timeout`"
            })
            return
        
        try:
            # Use the new smart response system
            smart_response = await self.ai_service.generate_smart_response(query)
            
            if smart_response["type"] == "historical_issues":
                # Format historical issues like before
                response = await self._format_search_results(query, smart_response["content"], user_id)
                await say({"blocks": response})
            else:
                # Handle all other response types with user mention
                await say({
                    "text": f"<@{user_id}> {smart_response['content']}"
                })
                
        except Exception as e:
            await say({
                "text": f"<@{user_id}> I apologize, but I'm experiencing a technical issue. Please try again in a moment, and I'll be happy to help you with your question!"
            })
    
    async def _handle_direct_message(self, say, event):
        """Handle direct messages to the bot"""
        text = event.get("text", "").strip()
        user_id = event.get("user")
        
        if not text or text.lower() in ["help", "hi", "hello"]:
            await say({
                "text": "👋 Hi! I'm SherlockAI, your advanced AI assistant!\n\n"
                       "*I can help you with ANYTHING:*\n"
                       "• Technical issues and debugging\n"
                       "• Code generation and programming help\n"
                       "• General questions and explanations\n"
                       "• Creative writing and brainstorming\n"
                       "• Learning and tutorials\n\n"
                       "*Just ask me anything - I'm like ChatGPT but with specialized knowledge!*\n\n"
                       "*Examples:*\n"
                       "• `How do I center a div in CSS?`\n"
                       "• `Explain quantum computing`\n"
                       "• `Write a Python function to sort a list`\n"
                       "• `What's the weather like?`\n"
                       "• `Help me debug this payment API error`"
            })
            return
        
        try:
            # Use the new smart response system
            smart_response = await self.ai_service.generate_smart_response(text)
            
            if smart_response["type"] == "historical_issues":
                # Format historical issues like before
                response = await self._format_search_results(text, smart_response["content"], user_id, is_dm=True)
                await say({"blocks": response})
            else:
                # Handle all other response types (conversational, code, general)
                await say({
                    "text": smart_response["content"]
                })
                
        except Exception as e:
            await say({
                "text": f"I apologize, but I'm experiencing a technical issue. Please try again in a moment, and I'll be happy to help you with your question!"
            })
    
    async def _search_issues(self, query: str, top_k: int = 3) -> list:
        """Search for similar issues using SherlockAI"""
        try:
            # Generate embedding for the query
            query_embedding = await self.ai_service.embed_text(query)
            
            # Search vector database
            results = await self.ai_service.search_similar(query_embedding, top_k=top_k)
            
            # Generate AI suggestions for each result
            enhanced_results = []
            for result in results:
                try:
                    # Generate AI suggestion
                    suggestion = await self._generate_ai_suggestion(result)
                    result['ai_suggestion'] = suggestion
                    enhanced_results.append(result)
                except Exception as e:
                    # If AI suggestion fails, still include the result
                    result['ai_suggestion'] = "Unable to generate AI suggestion at this time."
                    enhanced_results.append(result)
            
            return enhanced_results
            
        except Exception as e:
            print(f"Error searching issues: {e}")
            return []
    
    async def _generate_ai_suggestion(self, issue: Dict[str, Any]) -> str:
        """Generate AI-powered fix suggestion"""
        try:
            prompt = f"""You are a senior fintech engineer at Juspay. Here's a past incident:

Title: {issue.get('title', '')}
Description: {issue.get('description', '')}
Resolution: {issue.get('resolution', '')}

Based on this, write a 1-sentence actionable fix suggestion for a NEW engineer facing a similar issue. 
Start with 'Fix Suggestion: ' and be specific and practical."""

            suggestion = await self.ai_service.generate_text(
                prompt=prompt,
                max_tokens=100,
                temperature=0.2
            )
            
            return suggestion.strip()
            
        except Exception as e:
            return "Check the resolution details above for the fix approach."
    
    async def _format_search_results(self, query: str, results: list, user_id: str, is_dm: bool = False) -> list:
        """Format search results for Slack"""
        blocks = []
        
        # Header
        header_text = f"🔍 *Search Results for:* {query}"
        if not is_dm:
            header_text = f"🔍 *Search Results for <@{user_id}>:* {query}"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": header_text
            }
        })
        
        blocks.append({"type": "divider"})
        
        # Results
        for i, result in enumerate(results, 1):
            score = result.get('score', 0)
            title = result.get('title', 'No title')
            description = result.get('description', 'No description')
            resolution = result.get('resolution', 'No resolution')
            ai_suggestion = result.get('ai_suggestion', '')
            tags = result.get('tags', [])
            resolved_by = result.get('resolved_by', 'Unknown')
            
            # Truncate long text
            description = description[:200] + "..." if len(description) > 200 else description
            resolution = resolution[:300] + "..." if len(resolution) > 300 else resolution
            
            # Format tags
            tags_text = " ".join([f"`{tag}`" for tag in tags[:5]]) if tags else "No tags"
            
            # Result block
            result_text = f"*#{i} - {title}* (Match: {score:.1%})\n\n"
            result_text += f"*Problem:* {description}\n\n"
            result_text += f"*Resolution:* {resolution}\n\n"
            
            if ai_suggestion:
                result_text += f"🤖 *{ai_suggestion}*\n\n"
            
            result_text += f"*Tags:* {tags_text} | *Resolved by:* {resolved_by}"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": result_text
                }
            })
            
            if i < len(results):
                blocks.append({"type": "divider"})
        
        # Footer
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"🕒 Search completed in <1s | 🧠 Powered by SherlockAI | 💡 Found {len(results)} similar issues"
                }
            ]
        })
        
        # Feedback buttons
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "👍 Helpful"
                    },
                    "style": "primary",
                    "action_id": "feedback_helpful",
                    "value": json.dumps({"query": query, "helpful": True})
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "👎 Not Helpful"
                    },
                    "action_id": "feedback_not_helpful",
                    "value": json.dumps({"query": query, "helpful": False})
                }
            ]
        })
        
        return blocks
    
    async def start(self):
        """Start the Slack bot"""
        handler = AsyncSocketModeHandler(self.app, os.getenv("SLACK_APP_TOKEN"))
        await handler.start_async()

# Standalone script for running the bot
async def main():
    """Main function to run the Slack bot"""
    print("🚀 Starting SherlockAI Slack Bot...")
    
    # Check environment variables
    required_vars = ["SLACK_BOT_TOKEN", "SLACK_APP_TOKEN", "SLACK_SIGNING_SECRET"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("\nPlease set the following in your .env file:")
        for var in missing_vars:
            print(f"  {var}=your_token_here")
        return
    
    # Initialize database
    await init_database()
    
    # Start the bot
    bot = SherlockAISlackBot()
    
    print("✅ SherlockAI Slack Bot is running!")
    print("📱 Available commands:")
    print("   • /sherlock <query> - Search for solutions")
    print("   • @SherlockAI <query> - Mention the bot")
    print("   • Direct message the bot")
    print("\n🔗 Make sure to invite the bot to your channels!")
    
    await bot.start()

if __name__ == "__main__":
    asyncio.run(main())
