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


def flatten_metadata(issue: Dict) -> Dict[str, Any]:
	"""Flatten complex metadata fields for Pinecone compatibility"""
	metadata = {}
	
	# Simple fields that can be stored directly
	simple_fields = ["id", "title", "description", "created_at", "priority", "gateway", "jira_ticket", "sample_order"]
	for field in simple_fields:
		if field in issue:
			value = issue[field]
			if isinstance(value, (str, int, float, bool)):
				metadata[field] = value
			else:
				metadata[field] = str(value)
	
	# Handle tags as list of strings
	if "tags" in issue and isinstance(issue["tags"], list):
		metadata["tags"] = [str(tag) for tag in issue["tags"]]
	
	# Handle resolved_by (can be string or list)
	if "resolved_by" in issue:
		resolved_by = issue["resolved_by"]
		if isinstance(resolved_by, list):
			metadata["resolved_by"] = ", ".join(str(r) for r in resolved_by)
		else:
			metadata["resolved_by"] = str(resolved_by)
	
	# Convert complex fields to strings
	complex_fields = ["root_cause", "fix_applied", "ai_suggestion", "merchant_impact"]
	for field in complex_fields:
		if field in issue:
			metadata[field] = str(issue[field])
	
	# Handle error_patterns by converting to string representation
	if "error_patterns" in issue:
		patterns = issue["error_patterns"]
		if isinstance(patterns, list):
			pattern_strings = []
			for pattern in patterns:
				if isinstance(pattern, dict):
					pattern_str = f"Pattern: {pattern.get('pattern', '')}, Impact: {pattern.get('impact', '')}"
					pattern_strings.append(pattern_str)
				else:
					pattern_strings.append(str(pattern))
			metadata["error_patterns"] = pattern_strings
		else:
			metadata["error_patterns"] = str(patterns)
	
	# Handle systems_involved as list of strings
	if "systems_involved" in issue and isinstance(issue["systems_involved"], list):
		metadata["systems_involved"] = [str(system) for system in issue["systems_involved"]]
	
	# Handle stakeholders as list of strings
	if "stakeholders" in issue and isinstance(issue["stakeholders"], list):
		metadata["stakeholders"] = [str(stakeholder) for stakeholder in issue["stakeholders"]]
	
	return metadata


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
		
		# Flatten metadata for Pinecone compatibility
		metadata = flatten_metadata(issue)
		
		vectors.append({
			"id": issue["id"],
			"values": values,
			"metadata": metadata,
		})

	chunk = 100
	for i in range(0, len(vectors), chunk):
		index.upsert(vectors=vectors[i:i+chunk])
	print(f"Upserted {len(vectors)} issues into index '{index_name}'.")


if __name__ == "__main__":
	main()