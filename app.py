import os
import streamlit as st
import requests

API_URL = os.getenv("SherlockAI_API_URL", "http://localhost:8000/search")

st.set_page_config(page_title="SherlockAI", page_icon="🔍", layout="centered")
st.title("🔍 SherlockAI — Juspay’s AI Incident Assistant")

query = st.text_input("Describe the issue:", placeholder="e.g., UPI payment failed with error 5003")
top_k = st.slider("Results", 1, 5, 3)

if st.button("Search") or (query and st.session_state.get("auto_search")):
	if not query:
		st.warning("Please enter an issue description.")
	else:
		with st.spinner("Searching..."):
			resp = requests.post(API_URL, json={"query": query, "top_k": top_k}, timeout=30)
			resp.raise_for_status()
			results = resp.json().get("results", [])
			if not results:
				st.info("No similar past issues found.")
			else:
				for i, r in enumerate(results):
					st.subheader(f"#{i+1}: {r.get('title','Untitled')}")
					st.caption(f"Score: {r.get('score', 0):.3f}")
					st.write(f"💡 **AI Fix Suggestion:** {r.get('ai_suggestion','')}")
					tags = r.get('tags') or []
					if tags:
						st.write(f"🏷️ Tags: {', '.join(tags)}")
					st.markdown("---")
