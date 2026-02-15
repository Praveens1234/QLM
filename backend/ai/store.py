import sqlite3
import os
import json
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

class ChatStore:
    """
    Manages chat sessions and message history using SQLite.
    """

    def __init__(self, db_path: str = "data/chat.db"):
        self.db_path = db_path
        # Ensure data dir exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Sessions Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                title TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        ''')

        # Messages Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                role TEXT,
                content TEXT,
                tool_calls TEXT,
                tool_call_id TEXT,
                name TEXT,
                created_at TEXT,
                FOREIGN KEY(session_id) REFERENCES sessions(id)
            )
        ''')

        conn.commit()
        conn.close()

    def create_session(self, title: str = "New Chat") -> str:
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)',
                       (session_id, title, now, now))
        conn.commit()
        conn.close()
        return session_id

    def update_session_title(self, session_id: str, title: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?',
                       (title, datetime.now(timezone.utc).isoformat(), session_id))
        conn.commit()
        conn.close()

    def delete_session(self, session_id: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM messages WHERE session_id = ?', (session_id,))
        cursor.execute('DELETE FROM sessions WHERE id = ?', (session_id,))
        conn.commit()
        conn.close()

    def list_sessions(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM sessions ORDER BY updated_at DESC')
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def add_message(self, session_id: str, message: Dict[str, Any]):
        msg_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        role = message.get("role")
        content = message.get("content")
        tool_calls = json.dumps(message.get("tool_calls")) if message.get("tool_calls") else None
        tool_call_id = message.get("tool_call_id")
        name = message.get("name")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO messages (id, session_id, role, content, tool_calls, tool_call_id, name, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (msg_id, session_id, role, content, tool_calls, tool_call_id, name, now))

        # Update session timestamp
        cursor.execute('UPDATE sessions SET updated_at = ? WHERE id = ?', (now, session_id))

        conn.commit()
        conn.close()

    def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC', (session_id,))
        rows = cursor.fetchall()
        conn.close()

        history = []
        for row in rows:
            msg = {
                "role": row["role"],
                "content": row["content"]
            }
            if row["tool_calls"]:
                msg["tool_calls"] = json.loads(row["tool_calls"])
            if row["tool_call_id"]:
                msg["tool_call_id"] = row["tool_call_id"]
            if row["name"]:
                msg["name"] = row["name"]
            history.append(msg)

        return history
