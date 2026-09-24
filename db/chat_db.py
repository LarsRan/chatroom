"""SQLite chat history stored per local nickname."""
from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Any


class ChatDatabase:
    def __init__(self, username: str, root: Path | None = None):
        directory = Path(root or Path.home() / ".chatroom")
        directory.mkdir(parents=True, exist_ok=True)
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in username)[:32] or "guest"
        self.connection = sqlite3.connect(directory / f"{safe}.sqlite3", check_same_thread=False)
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY,
                sender TEXT,
                avatar TEXT,
                content TEXT,
                content_type TEXT,
                filename TEXT,
                timestamp TEXT
            )
            """
        )
        self.connection.commit()

    def add(self, message: dict[str, Any]) -> None:
        payload = {
            "sender": str(message.get("sender", "")),
            "avatar": str(message.get("avatar", "")),
            "content": str(message.get("content", "")),
            "content_type": str(message.get("content_type", "text")),
            "filename": str(message.get("filename", "")),
            "timestamp": str(message.get("timestamp", "")),
        }
        self.connection.execute(
            "INSERT INTO messages(sender,avatar,content,content_type,filename,timestamp) VALUES(?,?,?,?,?,?)",
            (
                payload["sender"],
                payload["avatar"],
                payload["content"],
                payload["content_type"],
                payload["filename"],
                payload["timestamp"],
            ),
        )
        self.connection.commit()

    def history(self) -> list[dict[str, str]]:
        rows = self.connection.execute(
            "SELECT sender,avatar,content,content_type,filename,timestamp FROM messages ORDER BY id"
        ).fetchall()
        return [
            {
                "type": "chat",
                "sender": row[0] or "",
                "avatar": row[1] or "",
                "content": row[2] or "",
                "content_type": row[3] or "text",
                "filename": row[4] or "",
                "timestamp": row[5] or "",
            }
            for row in rows
        ]

    def clear(self) -> None:
        self.connection.execute("DELETE FROM messages")
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()
