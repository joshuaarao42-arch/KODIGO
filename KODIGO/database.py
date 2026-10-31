"""History database."""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from typing import List, Optional

from .config import DB_PATH


class HistoryDB:
    def __init__(self, path=DB_PATH):
        self.path = str(path)
        with closing(self._connect()) as conn, conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS history (
                       id         INTEGER PRIMARY KEY AUTOINCREMENT,
                       created_at TEXT NOT NULL,
                       kind       TEXT NOT NULL,
                       title      TEXT NOT NULL,
                       payload    TEXT NOT NULL,
                       settings   TEXT NOT NULL,
                       thumbnail  BLOB,
                       signature  TEXT
                   )"""
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def add(self, kind: str, title: str, payload: str, settings: dict,
            thumbnail: bytes, signature: str) -> int:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with closing(self._connect()) as conn, conn:
            cur = conn.execute(
                "INSERT INTO history (created_at, kind, title, payload, settings, thumbnail, signature)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (now, kind, title, payload, json.dumps(settings), thumbnail, signature),
            )
            return cur.lastrowid

    def latest_signature(self) -> Optional[str]:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT signature FROM history ORDER BY id DESC LIMIT 1").fetchone()
            return row["signature"] if row else None

    def list(self, search: str = "", limit: int = 150) -> List[sqlite3.Row]:
        with closing(self._connect()) as conn:
            if search.strip():
                like = f"%{search.strip()}%"
                return conn.execute(
                    "SELECT * FROM history WHERE title LIKE ? OR payload LIKE ? OR kind LIKE ?"
                    " ORDER BY id DESC LIMIT ?",
                    (like, like, like, limit),
                ).fetchall()
            return conn.execute("SELECT * FROM history ORDER BY id DESC LIMIT ?", (limit,)).fetchall()

    def count(self) -> int:
        with closing(self._connect()) as conn:
            return conn.execute("SELECT COUNT(*) FROM history").fetchone()[0]

    def delete(self, entry_id: int) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute("DELETE FROM history WHERE id = ?", (entry_id,))

    def clear(self) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute("DELETE FROM history")
