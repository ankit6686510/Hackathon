import os
import json
from typing import List, Dict, Any
from dotenv import load_dotenv

import google.generativeai as genai
from pinecone import Pinecone, ServerlessSpec


def load_env() -> None:
	load_dotenv()
	missing = []
	for key in ["GEMINI_API_KEY", "PINECONE_API_KEY", "PINECONE_INDEX"]:
		if not os.getenv(key):
			missing.append(key)
	if missing:
		raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")


def read_issues(path: str) -> List[Dict]:
	with open(path, "r", encoding="utf-8") as f:
		return json.load(f)


def ensure_index(pc: Pinecone, index_name: str) -> None:
	indexes = {idx["name"] for idx in pc.list_indexes()}
	if index_name in indexes:
		return
	pc.create_index(
		name=index_name,
		dimension=768,
		metric="cosine",
		spec=ServerlessSpec(cloud="aws", region="us-east-1"),
	)


def build_text(issue: Dict) -> str:
	title = issue.get("title", "")
	desc = issue.get("description", "")
	res = issue.get("resolution", "")
	return f"Title: {title}\nDescription: {desc}\nFix: {res}"


def normalize_model(name: str, default: str) -> str:
	model = name or default
	return model if model.startswith("models/") else f"models/{model}"


def extract_single_embedding(resp: Any) -> List[float]:
	if isinstance(resp, dict):
		if "embedding" in resp:
			e = resp["embedding"]
			if isinstance(e, dict) and isinstance(e.get("values"), list):
				return e["values"]
			if isinstance(e, list):
				return e
		if "embeddings" in resp and resp["embeddings"]:
			first = resp["embeddings"][0]
			if isinstance(first, dict) and isinstance(first.get("values"), list):
				return first["values"]
	raise RuntimeError("Unexpected single embedding response format from Gemini")


def main() -> None:
	load_env()
	genai.configure(api_key=os.environ["GEMINI_API_KEY"]) 
	index_name = os.getenv("PINECONE_INDEX")
	pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"]) 

	ensure_index(pc, index_name)
	index = pc.Index(index_name)

	issues = read_issues(os.getenv("ISSUES_PATH", "issues.json"))
	model_name = normalize_model(os.getenv("GEMINI_EMBED_MODEL", "text-embedding-004"), "text-embedding-004")

	vectors = []
	for issue in issues:
		text = build_text(issue)
		resp = genai.embed_content(model=model_name, content=text)
		values = extract_single_embedding(resp)
		vectors.append({
			"id": issue["id"],
			"values": values,
			"metadata": issue,
		})

	chunk = 100
	for i in range(0, len(vectors), chunk):
		index.upsert(vectors=vectors[i:i+chunk])
	print(f"Upserted {len(vectors)} issues into index '{index_name}'.")


if __name__ == "__main__":
	main()
