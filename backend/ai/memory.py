from typing import Dict, Any, Optional
import json
import logging
from backend.database import db

logger = logging.getLogger("QLM.AI.JobManager")

class JobManager:
    """
    Manages long-running 'Jobs' or 'Goals' for the AI Agent.
    Persists state to SQLite to survive restarts.
    """
    def __init__(self):
        pass # Database connection handled per method via db.get_connection()

    def start_job(self, session_id: str, goal: str):
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO jobs (session_id, goal, status, steps_completed, artifacts)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    goal=excluded.goal,
                    status='in_progress',
                    steps_completed='[]',
                    artifacts='{}',
                    updated_at=CURRENT_TIMESTAMP
            ''', (session_id, goal, "in_progress", json.dumps([]), json.dumps({})))
            conn.commit()

        logger.info(f"Job started for session {session_id}: {goal}")

    def update_job(self, session_id: str, step_desc: str, artifacts: Optional[Dict] = None):
        with db.get_connection() as conn:
            cursor = conn.cursor()

            # Fetch current
            cursor.execute("SELECT steps_completed, artifacts FROM jobs WHERE session_id=?", (session_id,))
            row = cursor.fetchone()

            if not row:
                logger.warning(f"Attempted to update non-existent job for session {session_id}")
                return

            steps = json.loads(row["steps_completed"])
            current_artifacts = json.loads(row["artifacts"])

            # Update
            steps.append(step_desc)
            if artifacts:
                current_artifacts.update(artifacts)

            cursor.execute('''
                UPDATE jobs
                SET steps_completed=?, artifacts=?, updated_at=CURRENT_TIMESTAMP
                WHERE session_id=?
            ''', (json.dumps(steps), json.dumps(current_artifacts), session_id))

            conn.commit()

    def get_job_context(self, session_id: str) -> str:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs WHERE session_id=? AND status='in_progress'", (session_id,))
            row = cursor.fetchone()

            if not row:
                return ""

            steps = json.loads(row["steps_completed"])
            artifacts = json.loads(row["artifacts"])

            return f"""
            [ACTIVE JOB CONTEXT]
            Goal: {row["goal"]}
            Progress: {len(steps)} steps completed.
            Last Step: {steps[-1] if steps else 'Started'}
            Known Artifacts: {json.dumps(artifacts)}
            """

    def complete_job(self, session_id: str):
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE jobs SET status='completed', updated_at=CURRENT_TIMESTAMP WHERE session_id=?", (session_id,))
            conn.commit()
