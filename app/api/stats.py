"""
Stats endpoint — aggregate metrics from the reviews table.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import Review, get_db

router = APIRouter()


@router.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    """Return aggregate metrics across all reviews."""
    total_reviews = db.query(func.count(Review.id)).scalar() or 0
    total_comments = db.query(func.sum(Review.comments_posted)).scalar() or 0
    total_files = db.query(func.sum(Review.files_reviewed)).scalar() or 0
    avg_latency = db.query(func.avg(Review.latency_ms)).scalar() or 0

    recent = (
        db.query(Review)
        .order_by(Review.created_at.desc())
        .limit(10)
        .all()
    )

    return {
        "total_reviews": total_reviews,
        "total_comments": total_comments,
        "total_files_reviewed": total_files,
        "avg_latency_ms": round(avg_latency, 2),
        "recent_reviews": [
            {
                "repo": review.repo,
                "pr_number": review.pr_number,
                "comments_posted": review.comments_posted,
                "severity_breakdown": review.severity_breakdown,
                "latency_ms": review.latency_ms,
                "created_at": (
                    review.created_at.isoformat()
                    if review.created_at
                    else None
                ),
            }
            for review in recent
        ],
    }
