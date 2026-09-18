"""SQLite persistence for completed change-impact analyses."""

import json
import sqlite3
from pathlib import Path


DATABASE_PATH = Path(__file__).with_name("analyses.db")


def _connect():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    """Create the analyses table when the application starts."""
    connection = _connect()
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                change_description TEXT NOT NULL,
                target_node TEXT NOT NULL,
                result_json TEXT NOT NULL
            )
            """
        )
        connection.commit()
    finally:
        connection.close()


def save_analysis(change_description: str, result: dict) -> int:
    """Store an analysis result and return its database ID."""
    connection = _connect()
    try:
        cursor = connection.execute(
            """
            INSERT INTO analyses (change_description, target_node, result_json)
            VALUES (?, ?, ?)
            """,
            (
                change_description,
                result["targeted_node"],
                json.dumps(result, ensure_ascii=False),
            ),
        )
        connection.commit()
        return cursor.lastrowid
    finally:
        connection.close()


def get_recent_analyses(limit: int = 10) -> list[dict]:
    """Return the newest persisted analyses with their decoded results."""
    connection = _connect()
    try:
        rows = connection.execute(
            """
            SELECT id, timestamp, change_description, target_node, result_json
            FROM analyses
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        connection.close()

    return [
        {
            "id": row["id"],
            "timestamp": row["timestamp"],
            "change_description": row["change_description"],
            "target_node": row["target_node"],
            "result": json.loads(row["result_json"]),
        }
        for row in rows
    ]
