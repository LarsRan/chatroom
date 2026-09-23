"""SQLite chat history stored per local nickname."""
from pathlib import Path
import sqlite3

class ChatDatabase:
    def __init__(self, username, root=None):
        directory = Path(root or Path.home() / ".chatroom"); directory.mkdir(parents=True, exist_ok=True)
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in username)[:32] or "guest"
        self.connection = sqlite3.connect(directory / f"{safe}.sqlite3", check_same_thread=False)
        self.connection.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, sender TEXT, avatar TEXT, content TEXT, content_type TEXT, filename TEXT, timestamp TEXT)")
        self.connection.commit()
    def add(self, message):
        self.connection.execute("INSERT INTO messages(sender,avatar,content,content_type,filename,timestamp) VALUES(?,?,?,?,?,?)", tuple(message.get(k, "") for k in ("sender","avatar","content","content_type","filename","timestamp"))); self.connection.commit()
    def history(self):
        rows = self.connection.execute("SELECT sender,avatar,content,content_type,filename,timestamp FROM messages ORDER BY id").fetchall(); keys = ("sender","avatar","content","content_type","filename","timestamp")
        return [dict(zip(keys, row)) for row in rows]
    def clear(self): self.connection.execute("DELETE FROM messages"); self.connection.commit()
    def close(self): self.connection.close()
