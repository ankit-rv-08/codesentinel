"""
Core LLM review engine.

Takes a code diff (a string) and returns a list of structured review comments.
Uses Gemini 1.5 Flash for speed and cost.
"""

import json
import os
from typing import Dict, List

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini once at module load
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

REVIEW_PROMPT = """You are a senior software engineer reviewing a pull request diff.

Analyze the diff below and return a JSON object with this exact schema:

{{
  "comments": [
	{
	  "line": <integer line number in the new file>,
	  "severity": "info" | "warning" | "error",
	  "category": "bug" | "style" | "security" | "test" | "performance",
	  "message": "<specific, actionable comment>"
	}
  ]
}}

Rules:
- Only comment on real issues. Do not invent problems.
- Be specific. "This variable is unused" is good. "Consider improving this" is bad.
- If the diff is clean, return {"comments": []}.
- Return ONLY the JSON. No markdown, no explanation.

Diff:
```

{diff}

```
"""


def review_diff(diff: str) -> List[Dict]:
	"""
	Send a diff to Gemini and return a list of structured comments.

	Args:
		diff: A unified diff string (e.g. output of `git diff`).

	Returns:
		A list of comment dicts, each with keys: line, severity, category, message.
		Returns an empty list if the diff is empty or parsing fails.
	"""
	if not diff.strip():
		return []

	model = genai.GenerativeModel("gemini-3.6-flash")
	prompt = REVIEW_PROMPT.replace("{diff}", diff)

	try:
		response = model.generate_content(prompt)
		raw = response.text.strip()
	except Exception as e:
		print(f"[reviewer] Gemini call failed: {e}")
		return []

	# Strip markdown code fences if the model wrapped the JSON
	if raw.startswith("```"):
		raw = raw.split("```")[1]
		if raw.startswith("json"):
			raw = raw[4:]
		raw = raw.strip()

	try:
		data = json.loads(raw)
		return data.get("comments", [])
	except json.JSONDecodeError as e:
		print(f"[reviewer] JSON parse failed: {e}\nRaw: {raw[:200]}")
		return []


if __name__ == "__main__":
	# Quick manual test
	test_diff = """
+ import os
+ def get_user(id):
+     user = db.query(id)
+     return user.name
	"""
	comments = review_diff(test_diff)
	print(json.dumps(comments, indent=2))
