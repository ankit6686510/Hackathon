import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import requests

load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")  # xapp- token for Socket Mode
API_URL = os.getenv("SherlockAI_API_URL", "http://localhost:8000/search")

if not SLACK_BOT_TOKEN:
	raise RuntimeError("Missing SLACK_BOT_TOKEN in environment")
if not SLACK_APP_TOKEN:
	raise RuntimeError("Missing SLACK_APP_TOKEN (Socket Mode) in environment")

app = App(token=SLACK_BOT_TOKEN)


@app.command("/SherlockAI")
def handle_SherlockAI(ack, respond, command):
	ack()
	query = (command.get("text") or "").strip()
	if not query:
		respond("Usage: /SherlockAI <payment issue description>\n\n*SherlockAI* is specialized for payment-related issues only (UPI, cards, wallets, gateways, etc.)")
		return
	
	try:
		resp = requests.post(API_URL, json={"query": query, "top_k": 3}, timeout=30)
		resp.raise_for_status()
		data = resp.json()
		
		response_type = data.get("response_type")
		
		if response_type == "domain_rejection":
			# Non-payment query rejected
			respond(f"❌ *Payment Domain Only*\n\n{data.get('message', 'This query is not related to payment systems.')}\n\n💡 *Try asking about:* UPI failures, card declines, gateway timeouts, wallet issues, etc.")
			return
			
		elif response_type == "historical_payment_issues":
			# Found historical payment issues
			results = data.get("results", [])
			if not results:
				respond("No similar payment issues found in our history.")
				return
				
			lines = ["🔍 *SherlockAI - Historical Payment Issues Found:*\n"]
			for i, r in enumerate(results, 1):
				confidence = r.get('confidence_score', 0)
				confidence_emoji = "🟢" if confidence > 0.8 else "🟡" if confidence > 0.6 else "🔴"
				lines.append(f"{confidence_emoji} *#{i}: {r.get('title', 'Untitled')}*")
				lines.append(f"   💡 *Fix:* {r.get('ai_suggestion', 'No suggestion available')}")
				lines.append(f"   📊 *Confidence:* {confidence:.1%}")
				if r.get('tags'):
					lines.append(f"   🏷️ *Tags:* {', '.join(r['tags'])}")
				lines.append("")
			
			lines.append("⚠️ *Note:* These are AI-generated suggestions based on historical data. Please verify before implementing.")
			respond("\n".join(lines))
			
		elif response_type == "ai_payment_solution":
			# New payment issue with AI-generated solution
			solution = data.get("ai_solution", "")
			pending_id = data.get("pending_issue_id")
			confidence = data.get("confidence_level", 0)
			
			confidence_emoji = "🟢" if confidence > 0.7 else "🟡" if confidence > 0.5 else "🔴"
			
			lines = [
				"🤖 *SherlockAI - AI Payment Solution (New Issue):*\n",
				f"{confidence_emoji} *AI Suggestion:* {solution}",
				f"📊 *Confidence Level:* {confidence:.1%}",
				"",
				"⚠️ *Important:* This is an AI-generated solution for a new payment issue. We are not 100% sure of its accuracy.",
				"✅ Please verify this solution before implementing in production.",
				""
			]
			
			if pending_id:
				lines.append(f"📝 *Tracking ID:* {pending_id} (stored for future learning)")
			
			respond("\n".join(lines))
			
		else:
			respond("❌ Unexpected response format from SherlockAI API.")
			
	except requests.exceptions.Timeout:
		respond("⏱️ Request timed out. Please try again.")
	except requests.exceptions.RequestException as e:
		respond(f"🔌 Connection error: {str(e)}")
	except Exception as e:
		respond(f"❌ Error: {str(e)}")


# Keep the old command for backward compatibility but redirect to new one
@app.command("/SherlockAI")
def handle_SherlockAI_legacy(ack, respond, command):
	ack()
	respond("🔄 *Command Updated!*\n\nPlease use `/SherlockAI` instead of `/SherlockAI`\n\n*SherlockAI* is now specialized for payment-related issues only.\n\nUsage: `/SherlockAI <payment issue description>`")


def main():
	"""
	Start the SherlockAI Slack bot in Socket Mode.
	
	The bot provides payment domain-specific issue resolution:
	- /SherlockAI <query> - Search for payment issue solutions
	- Domain validation ensures only payment-related queries are processed
	- AI-generated solutions include confidence levels and disclaimers
	"""
	print("🚀 Starting SherlockAI Slack Bot...")
	print("📡 Available commands:")
	print("   /SherlockAI <payment issue description>")
	print("💳 Specialized for payment domain issues only")
	
	handler = SocketModeHandler(app, SLACK_APP_TOKEN)
	handler.start()


if __name__ == "__main__":
	main()
