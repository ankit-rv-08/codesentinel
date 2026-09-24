"""
Database setup for CodeSentinel.

Uses DATABASE_URL env var. On Render, this is a PostgreSQL URL.
Locally, it defaults to SQLite.
"""

import os
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./codesentinel.db")

# Render uses postgres://, SQLAlchemy needs postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {},
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    repo = Column(String, index=True, nullable=False)
    pr_number = Column(Integer, nullable=False)
    files_reviewed = Column(Integer, default=0)
    comments_posted = Column(Integer, default=0)
    severity_breakdown = Column(JSON, default=dict)
    model_used = Column(String, nullable=True)
    latency_ms = Column(Integer, default=0)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
