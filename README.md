<p align="center">
	<img src="codesentinel-icon.png" width="120" alt="CodeSentinel" />
</p>

<h1 align="center">CodeSentinel</h1>
<p align="center"><strong>AI-powered code review GitHub App</strong></p>

<p align="center">
	<a href="https://github.com/ankit-rv-08/codesentinel/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License" /></a>
	<img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python" />
	<img src="https://img.shields.io/badge/FastAPI-0.115-009688" alt="FastAPI" />
	<img src="https://img.shields.io/badge/Groq-GPT--OSS--120B-orange" alt="Groq" />
</p>

---

CodeSentinel is a GitHub App that reviews pull requests automatically. When a PR is opened or updated, it fetches the diff, sends it to an LLM, and posts structured inline comments on bugs, style issues, security problems, and missing tests.

**End-to-end verified.** See [#1](https://github.com/ankit-rv-08/codesentinel/pull/1) for a working example — the bot posted three inline comments on a test file with deliberate bugs.

---

## What it does

1. GitHub sends a `pull_request` webhook when a PR is opened or synchronized
2. The FastAPI server verifies the webhook's HMAC signature
3. It fetches the PR diff via the GitHub API
4. Each changed file is sent to an LLM with a structured review prompt
5. The LLM returns JSON comments with severity, category, and message
6. Comments are posted back on the PR at the exact line

---

## What it catches

| Severity | Category | Example |
|---|---|---|
| **error** | bug | Undefined variable, null dereference |
| **error** | security | SQL injection, hardcoded secrets |
| **warning** | bug | Division by zero, missing null check |
| **warning** | performance | O(n²) loops, redundant queries |
| **info** | style | Unused imports, naming, formatting |
| **info** | test | Missing tests for new code paths |

Each comment follows the format:

```text
SEVERITY (category): specific, actionable message
```

For example:

```text
ERROR (bug): Variable 'db' is referenced but not defined or imported. This will raise NameError at runtime.
WARNING (bug): If db.query(id) returns None, accessing user.name will raise AttributeError.
INFO (style): Unused import: os is imported but never used.
```

---

## Architecture

```text
GitHub PR opened
│
▼
GitHub sends pull_request webhook
│
▼
Cloudflare Tunnel → localhost:8000
│
▼
FastAPI /webhook endpoint
│ verifies HMAC signature
▼
GitHub API → fetch PR diff
│
▼
Groq LLM review (model fallback chain)
│ gpt-oss-120b → gpt-oss-20b → qwen3.8-27b
▼
GitHub API → post inline comments
│
▼
Comments appear on the PR
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Web framework | FastAPI |
| GitHub integration | PyGithub + GitHub App |
| LLM | Groq GPT-OSS-120B (fallback chain) |
| Tunnel (dev) | Cloudflare Tunnel |
| Language | Python 3.11+ |

---

## Model fallback chain

Regional model availability varies. CodeSentinel tries each model in order and uses the first that responds:

1. `openai/gpt-oss-120b` — strongest reasoning
2. `openai/gpt-oss-20b` — smaller, faster
3. `qwen/qwen3.8-27b` — final fallback

This makes the app resilient to regional outages and quota limits.

---

## Local setup

**Prerequisites:**
- Python 3.11+
- A GitHub App (create at github.com/settings/apps)
- A Groq API key (console.groq.com)
- Cloudflare Tunnel (`brew install cloudflared`)

**1. Clone and install**

```bash
git clone https://github.com/ankit-rv-08/codesentinel.git
cd codesentinel
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**2. Configure environment**

Create `.env` in the project root:

```text
GROQ_API_KEY=your_groq_key
GITHUB_APP_ID=your_app_id
GITHUB_PRIVATE_KEY_PATH=github-app.pem
GITHUB_WEBHOOK_SECRET=your_webhook_secret
```

Place the GitHub App's private key at `github-app.pem` in the project root. This file is gitignored — never commit it.

**3. Start the tunnel**

```bash
cloudflared tunnel --url http://localhost:8000
```

Copy the generated URL (e.g., `https://abc-xyz.trycloudflare.com`). Set it as the Webhook URL in your GitHub App settings, with `/webhook` appended:

```text
https://abc-xyz.trycloudflare.com/webhook
```

**4. Start the server**

```bash
uvicorn app.main:app --reload --port 8000
```

**5. Install the App**

Go to your GitHub App settings → Install App → install on a test repo.

**6. Test it**

Open a PR on the test repo with a deliberate bug. Watch the FastAPI terminal — you'll see the webhook arrive, the LLM review run, and the comments post.

## End-to-end verification

Test PR: [#1](https://github.com/ankit-rv-08/codesentinel/pull/1)

The diff added:

```python
import os

def get_user(id):
		user = db.query(id)
		return user.name
```

The bot posted three inline comments:

- Line 1: INFO (style): Unused import: os is imported but never used.
- Line 4: ERROR (bug): Variable 'db' is referenced but not defined or imported.
- Line 5: WARNING (bug): If db.query(id) returns None, accessing user.name will raise AttributeError.

## Project structure

```text
codesentinel/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI entry point
│   ├── github/
│   │   ├── __init__.py
│   │   └── webhook.py             # Webhook handler, GitHub API integration
│   └── llm/
│       ├── __init__.py
│       └── reviewer.py            # LLM review engine with model fallback
├── tests/
│   └── test_reviewer.py
├── codesentinel-icon.png
├── github-app.pem                 # gitignored
├── requirements.txt
├── .env                           # gitignored
├── .env.example
├── .gitignore
├── LICENSE
└── README.md
```

## Status

☑ Core LLM review engine (Groq GPT-OSS-120B)<br>
☑ Model fallback chain for regional availability<br>
☑ GitHub App registration and installation<br>
☑ Webhook handler with HMAC signature verification<br>
☑ PR diff fetching via GitHub API<br>
☑ Structured JSON review output<br>
☑ Inline comment posting<br>
☑ End-to-end tested on a real PR<br>
□ PostgreSQL review logging<br>
□ Metrics dashboard (Next.js)<br>
□ Rate limiting per installation<br>
□ Config file (`.codesentinel.yml`) for custom severity thresholds<br>
□ Support for GitHub Enterprise

## Roadmap

### v0.2 — Persistence

Log every review to PostgreSQL (repo, PR number, comments, latency, model used). Expose `/api/stats` endpoint for telemetry.

### v0.3 — Dashboard

Next.js dashboard showing PRs reviewed, top issue categories, average response time, and model usage.

### v0.4 — Configuration

`.codesentinel.yml` in the repo to control which categories to review, severity thresholds, and file exclusions.

### v0.5 — Rate limiting

Per-installation limits to prevent abuse on shared infrastructure.

## Design decisions

### Why Groq, not OpenAI or Gemini?

Groq's free tier has enough headroom for real use, and GPT-OSS-120B is a strong reasoning model. The fallback chain handles regional availability issues.

### Why a model fallback chain?

Regional availability varies. Model IDs that work from one region may not work from another. A fallback chain means the app never fails silently — it just uses the next best model.

### Why HMAC signature verification?

GitHub signs every webhook with a shared secret. Verifying the signature ensures the request actually came from GitHub and not from an attacker trying to trigger reviews.

### Why read the PEM file into memory instead of passing the path?

PyGithub has had issues with relative PEM paths and newline handling. Reading the file into a string and passing it directly avoids the `InvalidKeyError` that comes up when the file has unexpected whitespace.

## License

MIT.

---
