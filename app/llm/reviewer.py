"""
Core LLM review engine.

Takes a code diff (a string) and returns a list of structured review comments.
Uses a ranked fallback chain of Groq models verified as available on this account.
"""

import json
import os
from typing import Dict, List

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Verified against this account's /v1/models response.
# Best reasoning model first, smaller/cheaper models as fallback.
MODEL_FALLBACK_CHAIN = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
]

REVIEW_PROMPT = """You are a senior software engineer reviewing a pull request diff.

Analyze the diff below and return a JSON object with this exact schema:

{
  "comments": [
    {
      "line": <integer line number in the new file>,
      "severity": "info" | "warning" | "error",
      "category": "bug" | "style" | "security" | "test" | "performance",
      "message": "<specific, actionable comment>"
    }
  ]
}

SEVERITY RULES (follow these strictly):
- "error": code that will crash, corrupt data, or create a security vulnerability
- "warning": code that works but is fragile, inefficient, or likely to cause bugs later
- "info": minor style, readability, or documentation issues

CATEGORY RULES:
- "bug": logic errors, null dereferences, undefined variables, type mismatches
- "security": injection, hardcoded secrets, missing auth, unsafe eval
- "performance": O(n²) loops, redundant queries, unbounded memory
- "style": unused imports, naming, formatting
- "test": missing tests for new code paths

FEW-SHOT EXAMPLES:

Input diff: "+ import os\\n+ def get_user(id):\\n+     user = db.query(id)\\n+     return user.name"

Correct output:
{"comments": [
    {"line": 1, "severity": "info", "category": "style", "message": "Unused import: os is imported but never used."},
    {"line": 3, "severity": "error", "category": "bug", "message": "Variable 'db' is referenced but not defined or imported. This will raise NameError at runtime."},
    {"line": 4, "severity": "warning", "category": "bug", "message": "If db.query(id) returns None, accessing user.name will raise AttributeError. Add a null check."}
]}

Input diff: "+ def divide(a, b):\\n+     return a / b"

Correct output:
{"comments": [
    {"line": 2, "severity": "warning", "category": "bug", "message": "Division by zero is not handled. If b is 0, this raises ZeroDivisionError. Add a check before dividing."}
]}

Input diff: "+ def add(a, b):\\n+     return a + b"

Correct output:
{"comments": []}

RULES:
- Only comment on real issues. Do not invent problems.
- Be specific. Name the variable, the function, the exact risk.
- If the diff is clean, return {"comments": []}.
- Return ONLY the JSON. No markdown, no explanation.

Diff:
{diff}
"""


def review_diff(diff: str) -> List[Dict]:
    """Send a diff to Groq with model fallback and return structured comments."""
    if not diff.strip():
        return []

    prompt = REVIEW_PROMPT.replace("{diff}", diff)

    raw = None
    used_model = None

    for model_id in MODEL_FALLBACK_CHAIN:
        try:
            response = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2000,
            )
            raw = response.choices[0].message.content.strip()
            used_model = model_id
            break
        except Exception as e:
            print(f"[reviewer] Model {model_id} failed: {e}")
            continue
    if raw is None:
        print("[reviewer] All models in fallback chain failed.")
        return []

    print(f"[reviewer] Succeeded with {used_model}")

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
        print(f"[reviewer] JSON parse failed: {e}\nRaw: {raw[:300]}")
        return []


if __name__ == "__main__":
    test_diff = """
+ import os
+ def get_user(id):
+     user = db.query(id)
+     return user.name
    """
    comments = review_diff(test_diff)
    print(json.dumps(comments, indent=2))
