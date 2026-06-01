import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_log (
    id        TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    user_id   TEXT NOT NULL,
    role      TEXT NOT NULL,
    query     TEXT NOT NULL,
    answer_snippet TEXT,
    sources   TEXT,
    truncated INTEGER NOT NULL DEFAULT 0,
    latency_ms REAL
);
"""


class AuditLogger:
    def __init__(self, db_path: str = "data/audit/audit.db"):
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = str(path)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def log(
        self,
        user_id: str,
        role: str,
        query: str,
        answer: str,
        sources: List[str],
        truncated: bool,
        latency_ms: float,
    ) -> str:
        row_id = str(uuid.uuid4())
        snippet = answer[:200] if answer else None
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO audit_log
                    (id, timestamp, user_id, role, query, answer_snippet,
                     sources, truncated, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row_id,
                    datetime.now(timezone.utc).isoformat(),
                    user_id,
                    role,
                    query,
                    snippet,
                    json.dumps(sources),
                    int(truncated),
                    latency_ms,
                ),
            )
        return row_id

    def recent(self, n: int = 50) -> List[Dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?", (n,)
            ).fetchall()
        return [dict(r) for r in rows]

    def stats(self) -> Dict:
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
            unique = conn.execute(
                "SELECT COUNT(DISTINCT user_id) FROM audit_log"
            ).fetchone()[0]
        return {"total_queries": total, "unique_users": unique}
