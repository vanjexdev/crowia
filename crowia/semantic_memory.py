import logging
import pathlib
import sqlite3
import threading
from datetime import datetime

log = logging.getLogger(__name__)

_DDL = """
CREATE TABLE IF NOT EXISTS messages (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    role     TEXT    NOT NULL,
    content  TEXT    NOT NULL,
    ts       TEXT    NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    content,
    content='messages',
    content_rowid='id'
);
CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
END;
CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, content) VALUES ('delete', old.id, old.content);
END;
"""


class SemanticMemory:
    """Drop-in replacement for ConversationHistory with SQLite + FTS5 search."""

    def __init__(self, path: pathlib.Path, max_turns: int = 10):
        self.path = path.with_suffix(".db")
        self.max_turns = max_turns
        self._lock = threading.Lock()
        self._conn = self._open()

    def _open(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.executescript(_DDL)
        conn.commit()
        return conn

    def add(self, role: str, content) -> None:
        if isinstance(content, list):
            text = " ".join(
                p.get("text", "") if isinstance(p, dict) else str(p)
                for p in content
            )
        else:
            text = str(content)
        ts = datetime.utcnow().isoformat()
        with self._lock:
            self._conn.execute(
                "INSERT INTO messages (role, content, ts) VALUES (?, ?, ?)",
                (role, text, ts),
            )
            self._conn.commit()
            self._trim()

    def _trim(self) -> None:
        limit = self.max_turns * 2
        self._conn.execute(
            "DELETE FROM messages WHERE id NOT IN "
            "(SELECT id FROM messages ORDER BY id DESC LIMIT ?)",
            (limit,),
        )
        self._conn.commit()

    def get_messages(self) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT role, content FROM messages ORDER BY id"
            ).fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in rows]

    def search(self, query: str, limit: int = 5) -> list[dict]:
        """Full-text search across past messages. Returns relevant turns."""
        with self._lock:
            try:
                rows = self._conn.execute(
                    "SELECT m.role, m.content FROM messages m "
                    "JOIN messages_fts f ON m.id = f.rowid "
                    "WHERE messages_fts MATCH ? "
                    "ORDER BY rank LIMIT ?",
                    (query, limit),
                ).fetchall()
            except sqlite3.OperationalError as e:
                log.warning("FTS search error: %s", e)
                return []
        return [{"role": r["role"], "content": r["content"]} for r in rows]

    def clear(self) -> None:
        with self._lock:
            self._conn.executescript(
                "DELETE FROM messages; "
                "INSERT INTO messages_fts(messages_fts) VALUES ('rebuild');"
            )
            self._conn.commit()
        log.info("SemanticMemory cleared")
