import sqlite3
from pathlib import Path
from datetime import datetime, timezone

class Database:
    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def connect(self):
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        return con

    def _init(self):
        with self.connect() as con:
            con.execute('''CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                title TEXT NOT NULL,
                details TEXT DEFAULT '',
                state TEXT NOT NULL DEFAULT 'open',
                created_at TEXT NOT NULL
            )''')

    def add_note(self, platform: str, title: str, details: str = "") -> int:
        with self.connect() as con:
            cur = con.execute(
                "INSERT INTO notes(platform,title,details,state,created_at) VALUES(?,?,?,?,?)",
                (platform, title, details, "open", datetime.now(timezone.utc).isoformat())
            )
            return int(cur.lastrowid)

    def list_notes(self, limit: int = 10):
        with self.connect() as con:
            return con.execute(
                "SELECT * FROM notes ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()

    def summary(self):
        with self.connect() as con:
            rows = con.execute(
                "SELECT platform,state,COUNT(*) AS n FROM notes GROUP BY platform,state"
            ).fetchall()
            return [dict(r) for r in rows]
