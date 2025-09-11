# 🤖 SherlockAI Slack Integration Setup Guide

## Connect SherlockAI to Your Slack Workspace

This guide will help you set up SherlockAI as a Slack bot so your team can query it directly from Slack channels using slash commands, mentions, or direct messages.

## 🚀 Quick Overview

Once set up, your team can:
- Use `/sherlock payment timeout error` in any channel
- Mention `@SherlockAI database connection issues` 
- Send direct messages to the bot
- Get instant AI-powered solutions with high relevance scores
- Share results with the team automatically

## 📋 Prerequisites

- Admin access to your Slack workspace
- SherlockAI backend running (this project)
- 10 minutes for setup

## 🔧 Step 1: Create Slack App

### 1.1 Go to Slack API
Visit [https://api.slack.com/apps](https://api.slack.com/apps) and click **"Create New App"**

### 1.2 Choose "From scratch"
- **App Name**: `SherlockAI` (or your preferred name)
- **Workspace**: Select your workspace
- Click **"Create App"**

### 1.3 Configure Basic Information
- **Display Name**: `SherlockAI`
- **Default Username**: `sherlockai`
- **Description**: `AI-powered issue intelligence assistant for instant solutions`

## 🔑 Step 2: Get API Tokens

### 2.1 Bot Token
1. Go to **"OAuth & Permissions"** in the left sidebar
2. Scroll down to **"Scopes"** → **"Bot Token Scopes"**
3. Add these scopes:
   ```
   app_mentions:read
   channels:history
   chat:write
   commands
   im:history
   im:read
   im:write
   users:read
   ```
4. Scroll up and click **"Install to Workspace"**
5. Copy the **"Bot User OAuth Token"** (starts with `xoxb-`)

### 2.2 App Token (for Socket Mode)
1. Go to **"Basic Information"** → **"App-Level Tokens"**
2. Click **"Generate Token and Scopes"**
3. **Token Name**: `socket-token`
4. **Scopes**: Add `connections:write`
5. Click **"Generate"**
6. Copy the **"App-Level Token"** (starts with `xapp-`)

### 2.3 Signing Secret
1. In **"Basic Information"** → **"App Credentials"**
2. Copy the **"Signing Secret"**

## ⚙️ Step 3: Configure Slack App

### 3.1 Enable Socket Mode
1. Go to **"Socket Mode"** in the left sidebar
2. Toggle **"Enable Socket Mode"** to **ON**

### 3.2 Create Slash Commands
1. Go to **"Slash Commands"** in the left sidebar
2. Click **"Create New Command"**

**Command 1:**
- **Command**: `/sherlock`
- **Request URL**: `https://your-domain.com/slack/events` (not needed for Socket Mode)
- **Short Description**: `Search for solutions to technical issues`
- **Usage Hint**: `payment timeout error`

**Command 2 (Optional):**
- **Command**: `/SherlockAI`
- **Request URL**: `https://your-domain.com/slack/events`
- **Short Description**: `Alternative command for SherlockAI`
- **Usage Hint**: `database connection issues`

### 3.3 Enable Events
1. Go to **"Event Subscriptions"** in the left sidebar
2. Toggle **"Enable Events"** to **ON**
3. Subscribe to these **Bot Events**:
   ```
   app_mention
   message.im
   ```

## 🔐 Step 4: Configure Environment Variables

Add these to your `.env` file:

```bash
# Slack Integration
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_APP_TOKEN=xapp-your-app-token-here
SLACK_SIGNING_SECRET=your-signing-secret-here
```

## 📦 Step 5: Install Dependencies

```bash
# Install Slack SDK
pip install slack-bolt slack-sdk

# Or add to requirements.txt
echo "slack-bolt>=1.18.0" >> requirements.txt
echo "slack-sdk>=3.21.0" >> requirements.txt
pip install -r requirements.txt
```

## 🚀 Step 6: Run the Slack Bot

### Option 1: Standalone Bot
```bash
# Run the Slack bot separately
python slack_integration.py
```

### Option 2: Integrated with Main App
```bash
# Add to your main application startup
# (We'll show this integration below)
```

## 🔗 Step 7: Invite Bot to Channels

1. Go to any Slack channel
2. Type: `/invite @SherlockAI`
3. Or go to channel settings → Integrations → Add apps → SherlockAI

## ✅ Step 8: Test the Integration

### Test Slash Commands
```
/sherlock payment gateway timeout
/sherlock database connection pool exhausted
/sherlock webhook delivery failing
```

### Test Mentions
```
@SherlockAI UPI payment failed with error 5003
@SherlockAI redis cache performance issues
```

### Test Direct Messages
1. Click on SherlockAI in your workspace
2. Send: `microservice circuit breaker issues`

## 🎯 Usage Examples

### In Engineering Channels
```
Engineer: /sherlock payment timeout HDFC bank
SherlockAI: 🔍 Search Results for @john.doe: payment timeout HDFC bank

#1 - Payment Gateway Timeout on HDFC Bank (Match: 79.4%)
Problem: Payment requests to HDFC bank timing out after 30 seconds...
Resolution: Increased timeout to 60 seconds and implemented retry logic...
🤖 Fix Suggestion: Increase gateway timeout to 60s and add exponential backoff retry logic.
```

### In Incident Channels
```
Engineer: @SherlockAI webhook delivery failing SSL certificate
SherlockAI: 🔍 Search Results for @jane.smith: webhook delivery failing SSL certificate

#1 - Webhook Delivery Failure to Merchant Endpoints (Match: 67.9%)
Problem: Webhook delivery failing for 3 major merchants due to SSL certificate validation errors...
Resolution: Added configurable SSL verification bypass for whitelisted merchant endpoints...
🤖 Fix Suggestion: Configure SSL verification bypass for trusted merchant endpoints.
```

## 🔧 Advanced Configuration

### Custom Response Format
Edit `slack_integration.py` to customize:
- Number of results returned (default: 3)
- Response formatting
- AI suggestion prompts
- Feedback collection

### Integration with Main App
Add to your `main.py`:

```python
import asyncio
from slack_integration import SherlockAISlackBot

async def start_slack_bot():
    """Start Slack bot alongside main app"""
    if all([
        os.getenv("SLACK_BOT_TOKEN"),
        os.getenv("SLACK_APP_TOKEN"), 
        os.getenv("SLACK_SIGNING_SECRET")
    ]):
        bot = SherlockAISlackBot()
        await bot.start()

# Add to your startup
if __name__ == "__main__":
    # Start main app
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
    # Start Slack bot in background
    asyncio.create_task(start_slack_bot())
```

## 📊 Monitoring & Analytics

The Slack bot automatically logs:
- Search queries and results
- User feedback (👍/👎 buttons)
- Response times
- Most common queries

Access analytics via your SherlockAI dashboard or database queries.

## 🔒 Security Best Practices

1. **Token Security**
   - Store tokens in environment variables, never in code
   - Use different tokens for dev/staging/production
   - Rotate tokens regularly

2. **Permissions**
   - Only grant necessary Slack scopes
   - Limit bot to specific channels if needed
   - Monitor bot usage and access logs

3. **Data Privacy**
   - Bot only accesses messages where it's mentioned
   - No message content is stored permanently
   - Search queries are logged for analytics only

## 🐛 Troubleshooting

### Bot Not Responding
1. Check environment variables are set correctly
2. Verify bot is invited to the channel
3. Check bot permissions and scopes
4. Look at application logs for errors

### Slash Commands Not Working
1. Verify commands are created in Slack app settings
2. Check Socket Mode is enabled
3. Ensure app is installed in workspace

### Permission Errors
1. Re-install app to workspace
2. Check bot token scopes
3. Verify app-level token has `connections:write`

### Common Error Messages
```bash
# Missing tokens
❌ Missing environment variables: SLACK_BOT_TOKEN, SLACK_APP_TOKEN

# Solution: Add tokens to .env file

# Connection errors
❌ Error connecting to Slack: Invalid token

# Solution: Verify token format and permissions
```

## 🎉 Success Metrics

Once working, you should see:
- ✅ Instant responses to `/sherlock` commands
- ✅ High relevance search results (70-80% match scores)
- ✅ AI-powered fix suggestions
- ✅ Team members using it regularly
- ✅ Reduced time to resolve incidents

## 🚀 Next Steps

1. **Train with More Data**: Use enterprise ingestion to add more historical issues
2. **Custom Commands**: Add domain-specific slash commands
3. **Integrations**: Connect with Jira, PagerDuty, or monitoring tools
4. **Analytics**: Set up dashboards for bot usage and effectiveness
5. **Feedback Loop**: Use 👍/👎 data to improve search quality

Your team now has SherlockAI available 24/7 in Slack for instant issue resolution! 🎯
