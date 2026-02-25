"""
SQLite database module for storing analysis results and user data.
Uses Python's built-in sqlite3 — no external dependencies required.
"""

import sqlite3
import os
from datetime import datetime, timezone
from contextlib import contextmanager

DB_PATH = os.getenv("DB_PATH", "financial_analyzer.db")


@contextmanager
def get_db():
    """Context manager for database connections with WAL mode for concurrent reads."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create tables if they don't exist. Called on app startup."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                username    TEXT UNIQUE NOT NULL,
                email       TEXT UNIQUE,
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS analyses (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id       TEXT UNIQUE NOT NULL,
                user_id       INTEGER REFERENCES users(id) ON DELETE SET NULL,
                filename      TEXT NOT NULL,
                file_size     INTEGER NOT NULL DEFAULT 0,
                query         TEXT NOT NULL,
                status        TEXT NOT NULL DEFAULT 'queued',
                analysis      TEXT,
                error         TEXT,
                created_at    TEXT NOT NULL DEFAULT (datetime('now')),
                completed_at  TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_analyses_task_id ON analyses(task_id);
            CREATE INDEX IF NOT EXISTS idx_analyses_user_id ON analyses(user_id);
            CREATE INDEX IF NOT EXISTS idx_analyses_status  ON analyses(status);
        """)


# ── User CRUD ──────────────────────────────────────────────────────────────────

def create_user(username: str, email: str = None) -> dict:
    """Create a new user. Returns the user dict."""
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO users (username, email) VALUES (?, ?)",
            (username, email),
        )
        row = conn.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return dict(row) if row else None


def get_user(user_id: int) -> dict | None:
    """Get a user by ID."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def get_user_by_username(username: str) -> dict | None:
    """Get a user by username."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return dict(row) if row else None


def list_users(limit: int = 50, offset: int = 0) -> list[dict]:
    """List all users with pagination."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]


# ── Analysis CRUD ──────────────────────────────────────────────────────────────

def create_analysis(task_id: str, filename: str, file_size: int, query: str, user_id: int = None) -> dict:
    """Record a new analysis submission."""
    with get_db() as conn:
        conn.execute(
            """INSERT INTO analyses (task_id, user_id, filename, file_size, query, status)
               VALUES (?, ?, ?, ?, ?, 'queued')""",
            (task_id, user_id, filename, file_size, query),
        )
        row = conn.execute("SELECT * FROM analyses WHERE task_id = ?", (task_id,)).fetchone()
        return dict(row) if row else None


def get_analysis(analysis_id: int) -> dict | None:
    """Get an analysis by its database ID."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
        return dict(row) if row else None


def get_analysis_by_task_id(task_id: str) -> dict | None:
    """Get an analysis by its Celery task ID."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM analyses WHERE task_id = ?", (task_id,)).fetchone()
        return dict(row) if row else None


def update_analysis_status(task_id: str, status: str, analysis: str = None, error: str = None):
    """Update analysis status. Sets completed_at when status is success or failed."""
    completed_at = datetime.now(timezone.utc).isoformat() if status in ("success", "failed") else None
    with get_db() as conn:
        conn.execute(
            """UPDATE analyses
               SET status = ?, analysis = COALESCE(?, analysis), error = COALESCE(?, error),
                   completed_at = COALESCE(?, completed_at)
               WHERE task_id = ?""",
            (status, analysis, error, completed_at, task_id),
        )


def list_analyses(
    user_id: int = None,
    status: str = None,
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    """List analyses with optional filters and pagination."""
    query = "SELECT * FROM analyses WHERE 1=1"
    params = []

    if user_id is not None:
        query += " AND user_id = ?"
        params.append(user_id)
    if status is not None:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_analysis_stats(user_id: int = None) -> dict:
    """Get analysis statistics, optionally filtered by user."""
    where = "WHERE user_id = ?" if user_id else ""
    params = [user_id] if user_id else []

    with get_db() as conn:
        row = conn.execute(
            f"""SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as succeeded,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN status IN ('queued','processing','retrying','pending') THEN 1 ELSE 0 END) as in_progress,
                    SUM(file_size) as total_bytes_processed
                FROM analyses {where}""",
            params,
        ).fetchone()
        return dict(row)


def delete_analysis(task_id: str) -> bool:
    """Delete an analysis record by task_id. Returns True if a row was deleted."""
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM analyses WHERE task_id = ?", (task_id,))
        return cursor.rowcount > 0
