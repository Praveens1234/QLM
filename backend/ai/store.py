import uuid
import json
from typing import List, Dict, Any
from datetime import datetime, timezone
from backend.database import db

class ChatStore:
    """
    Manages chat sessions and message history using the central SQLite DB.
    """

    def __init__(self):
        pass

    def create_session(self, title: str = "New Chat") -> str:
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)',
                           (session_id, title, now, now))
            conn.commit()
        return session_id

    def update_session_title(self, session_id: str, title: str):
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?',
                           (title, datetime.now(timezone.utc).isoformat(), session_id))
            conn.commit()

    def delete_session(self, session_id: str):
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM messages WHERE session_id = ?', (session_id,))
            cursor.execute('DELETE FROM sessions WHERE id = ?', (session_id,))
            conn.commit()

    def list_sessions(self) -> List[Dict[str, Any]]:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM sessions ORDER BY updated_at DESC')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def add_message(self, session_id: str, message: Dict[str, Any]):
        msg_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        role = message.get("role")
        content = message.get("content")
        tool_calls = json.dumps(message.get("tool_calls")) if message.get("tool_calls") else None
        tool_call_id = message.get("tool_call_id")
        name = message.get("name")

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO messages (id, session_id, role, content, tool_calls, tool_call_id, name, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (msg_id, session_id, role, content, tool_calls, tool_call_id, name, now))

            # Update session timestamp
            cursor.execute('UPDATE sessions SET updated_at = ? WHERE id = ?', (now, session_id))
            conn.commit()

    def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC', (session_id,))
            rows = cursor.fetchall()

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
