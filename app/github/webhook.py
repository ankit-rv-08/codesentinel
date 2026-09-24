"""
GitHub webhook handler.

Receives pull_request events, fetches the diff, runs the review engine,
posts comments back on the PR, and logs the review to the database.
"""

import os
import json
import hmac
import hashlib
import time
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from github import Github, GithubIntegration, Auth
from sqlalchemy.orm import Session

from app.db import Review, get_db
from app.llm.reviewer import review_diff

router = APIRouter()

GITHUB_APP_ID = int(os.getenv("GITHUB_APP_ID"))
PRIVATE_KEY_PATH = os.getenv("GITHUB_PRIVATE_KEY_PATH")
WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")


def load_private_key() -> str:
    """Read the PEM from an env var (deploy) or file path (local)."""
    env_key = os.getenv("GITHUB_PRIVATE_KEY")
    if env_key:
        return env_key.replace("\\n", "\n")

    path = Path(PRIVATE_KEY_PATH).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Private key not found at {path}")
    return path.read_text()


def verify_signature(payload: bytes, signature: str) -> bool:
    """Verify that the webhook came from GitHub."""
    if not signature:
        return False
    expected = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def get_installation_client(installation_id: int) -> Github:
    """Get an authenticated GitHub client for a specific installation."""
    private_key = load_private_key()
    auth = Auth.AppAuth(GITHUB_APP_ID, private_key)
    gi = GithubIntegration(auth=auth)
    installation = gi.get_app_installation(installation_id)
    return installation.get_github_for_installation()


@router.post("/webhook")
async def github_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_hub_signature_256: str = Header(None),
):
    """Handle GitHub webhook events."""
    start_time = time.time()
    payload = await request.body()

    if not verify_signature(payload, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid signature")

    event = json.loads(payload)

    if event.get("action") not in ("opened", "synchronize"):
        return {"status": "ignored", "reason": f"action={event.get('action')}"}

    pr_data = event["pull_request"]
    repo_full_name = event["repository"]["full_name"]
    pr_number = pr_data["number"]
    installation_id = event["installation"]["id"]

    print(f"[webhook] PR #{pr_number} in {repo_full_name} — action={event['action']}")

    try:
        gh = get_installation_client(installation_id)
        repo = gh.get_repo(repo_full_name)
        pr = repo.get_pull(pr_number)
    except Exception as e:
        print(f"[webhook] Failed to authenticate: {e}")
        raise HTTPException(status_code=500, detail=f"GitHub auth failed: {e}")

    total_comments = 0
    files_reviewed = 0
    severity_counts = {"error": 0, "warning": 0, "info": 0}
    model_used = None

    for file in pr.get_files():
        if not file.patch:
            continue

        files_reviewed += 1
        print(f"[webhook] Reviewing {file.filename}")

        comments = review_diff(file.patch)

        for comment in comments:
            severity = comment.get("severity", "info")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

            try:
                pr.create_review_comment(
                    body=f"**{severity.upper()}** ({comment['category']}): {comment['message']}",
                    commit=pr.head.sha,
                    path=file.filename,
                    line=comment["line"],
                )
                total_comments += 1
                print(
                    f"[webhook] Posted comment on "
                    f"{file.filename}:{comment['line']}"
                )
            except Exception as e:
                print(
                    f"[webhook] Failed to post comment on line "
                    f"{comment['line']}: {e}"
                )

    latency_ms = int((time.time() - start_time) * 1000)

    review = Review(
        repo=repo_full_name,
        pr_number=pr_number,
        files_reviewed=files_reviewed,
        comments_posted=total_comments,
        severity_breakdown=severity_counts,
        model_used=model_used or "fallback-chain",
        latency_ms=latency_ms,
    )
    db.add(review)
    db.commit()

    print(f"[webhook] Logged review: {total_comments} comments, {latency_ms}ms")

    return {
        "status": "reviewed",
        "pr": pr_number,
        "repo": repo_full_name,
        "comments_posted": total_comments,
        "latency_ms": latency_ms,
    }
