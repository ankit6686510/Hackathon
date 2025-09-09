import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import requests

load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")  # xapp- token for Socket Mode
API_URL = os.getenv("FIXGENIE_API_URL", "http://localhost:8000/search")

if not SLACK_BOT_TOKEN:
	raise RuntimeError("Missing SLACK_BOT_TOKEN in environment")
if not SLACK_APP_TOKEN:
	raise RuntimeError("Missing SLACK_APP_TOKEN (Socket Mode) in environment")

app = App(token=SLACK_BOT_TOKEN)


@app.command("/fixgenie")
def handle_fixgenie(ack, respond, command):
	ack()
	query = (command.get("text") or "").strip()
	if not query:
		respond("Usage: /fixgenie <issue description>")
		return
	try:
		resp = requests.post(API_URL, json={"query": query, "top_k": 3}, timeout=30)
		resp.raise_for_status()
		results = resp.json().get("results", [])
		if not results:
			respond("No similar past issues found.")
			return
		lines = ["*FixGenie Results:*\n"]
		for r in results:
			lines.append(f"• *{r.get('title','Untitled')}* — {r.get('ai_suggestion','')}")
		respond("\n".join(lines))
	except Exception as e:
		respond(f"Error: {e}")


def main():
	SocketModeHandler(app, SLACK_APP_TOKEN).start()


if __name__ == "__main__":
	main()
