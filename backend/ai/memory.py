from typing import Dict, Any, Optional
import json
import logging

logger = logging.getLogger("QLM.AI.JobManager")

class JobManager:
    """
    Manages long-running 'Jobs' or 'Goals' for the AI Agent.
    Helps maintain context across multiple turns and reasoning steps.
    """
    def __init__(self):
        self.active_jobs: Dict[str, Dict[str, Any]] = {}

    def start_job(self, session_id: str, goal: str):
        self.active_jobs[session_id] = {
            "goal": goal,
            "status": "in_progress",
            "steps_completed": [],
            "artifacts": {} # e.g. {"dataset_id": "...", "strategy_name": "..."}
        }
        logger.info(f"Job started for session {session_id}: {goal}")

    def update_job(self, session_id: str, step_desc: str, artifacts: Optional[Dict] = None):
        if session_id in self.active_jobs:
            self.active_jobs[session_id]["steps_completed"].append(step_desc)
            if artifacts:
                self.active_jobs[session_id]["artifacts"].update(artifacts)

    def get_job_context(self, session_id: str) -> str:
        job = self.active_jobs.get(session_id)
        if not job:
            return ""

        return f"""
        [ACTIVE JOB CONTEXT]
        Goal: {job['goal']}
        Progress: {len(job['steps_completed'])} steps completed.
        Last Step: {job['steps_completed'][-1] if job['steps_completed'] else 'Started'}
        Known Artifacts: {json.dumps(job['artifacts'])}
        """

    def complete_job(self, session_id: str):
        if session_id in self.active_jobs:
            del self.active_jobs[session_id]
