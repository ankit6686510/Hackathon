#!/usr/bin/env python3
"""
Quick Slack Bot Validation Test
Tests Slack bot configuration and provides manual testing instructions
"""

import os
from dotenv import load_dotenv

load_dotenv()

def validate_slack_configuration():
    print("🤖 SherlockAI Slack Bot Validation")
    print("=" * 50)
    
    # Check environment variables
    slack_bot_token = os.getenv("SLACK_BOT_TOKEN")
    slack_app_token = os.getenv("SLACK_APP_TOKEN")
    slack_signing_secret = os.getenv("SLACK_SIGNING_SECRET")
    
    print("🔧 Environment Variables:")
    if slack_bot_token and slack_bot_token.startswith('xoxb-'):
        print(f"   ✅ SLACK_BOT_TOKEN: {slack_bot_token[:20]}...{slack_bot_token[-4:]}")
    else:
        print("   ❌ SLACK_BOT_TOKEN: Missing or invalid format")
        return False
    
    if slack_app_token and slack_app_token.startswith('xapp-'):
        print(f"   ✅ SLACK_APP_TOKEN: {slack_app_token[:20]}...{slack_app_token[-4:]}")
    else:
        print("   ❌ SLACK_APP_TOKEN: Missing or invalid format")
        return False
    
    if slack_signing_secret and len(slack_signing_secret) >= 32:
        print(f"   ✅ SLACK_SIGNING_SECRET: {slack_signing_secret[:10]}...{slack_signing_secret[-4:]}")
    else:
        print("   ❌ SLACK_SIGNING_SECRET: Missing or too short")
        return False
    
    print()
    
    # Check if bot process is running
    import subprocess
    try:
        result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
        slack_processes = [line for line in result.stdout.split('\n') if 'slack_bot.py' in line and 'grep' not in line]
        
        if slack_processes:
            process_info = slack_processes[0].split()
            pid = process_info[1]
            print(f"🤖 Slack Bot Process: ✅ Running (PID: {pid})")
        else:
            print("🤖 Slack Bot Process: ❌ Not running")
            print("   💡 Run: python slack_bot.py")
            return False
    except Exception as e:
        print(f"🤖 Slack Bot Process: ❌ Error checking: {e}")
        return False
    
    print()
    print("🎉 Slack Bot Configuration: ✅ VALID")
    print()
    
    # Manual testing instructions
    print("📋 MANUAL TESTING INSTRUCTIONS:")
    print("=" * 50)
    print()
    print("1. 🔗 Go to your Slack workspace")
    print("2. 💬 Try these commands:")
    print("   • /SherlockAI payment timeout error")
    print("   • /SherlockAI database connection failed")
    print("   • @SherlockAI UPI payment issue")
    print()
    print("3. ✅ Expected Bot Behavior:")
    print("   • Bot should respond within 5-10 seconds")
    print("   • Should show search results or AI suggestions")
    print("   • May show 'backend unavailable' if API is down")
    print("   • Should handle non-payment queries appropriately")
    print()
    print("4. 🐛 If Bot Doesn't Respond:")
    print("   • Check bot is invited to the channel (/invite @SherlockAI)")
    print("   • Verify Socket Mode is enabled in Slack app settings")
    print("   • Check bot permissions include 'chat:write' and 'commands'")
    print("   • Restart bot: python slack_bot.py")
    print()
    print("5. 🔧 Backend Issues (Expected):")
    print("   • Backend API may be unavailable (port 8000 issues)")
    print("   • Bot will still respond with error messages")
    print("   • This is a configuration issue, not a Slack bot issue")
    print()
    
    return True

def main():
    success = validate_slack_configuration()
    
    if success:
        print("🎯 RESULT: Slack bot is properly configured!")
        print("🚀 Ready for manual testing in Slack workspace.")
        print()
        print("💡 Next Steps:")
        print("   1. Test slash commands in Slack")
        print("   2. Fix backend API connectivity separately")
        print("   3. Re-test full integration once backend is stable")
    else:
        print("❌ RESULT: Configuration issues found.")
        print("🔧 Please fix the issues above and try again.")

if __name__ == "__main__":
    main()
