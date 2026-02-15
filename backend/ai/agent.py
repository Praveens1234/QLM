import logging
import json
import traceback
from typing import List, Dict, Any, Optional, Callable, Awaitable
from backend.ai.client import AIClient
from backend.ai.tools import AITools
from backend.ai.store import ChatStore
from backend.ai.brain import Brain
from backend.ai.memory import JobManager
from backend.ai.config_manager import AIConfigManager
import os

logger = logging.getLogger("QLM.AI.Agent")

# Base Prompt
BASE_PROMPT = """
You are a **Senior Quantitative Researcher (Agent)** for the QLM Framework.
Your goal is to autonomously develop, validate, and optimize trading strategies.

You have access to a powerful set of tools. You must use them responsibly.
Use the **ReAct (Reasoning + Acting)** pattern: Thought -> Tool -> Observation.

**Critical Rules:**
1.  **Always** validate a strategy (`validate_strategy`) before running a backtest.
2.  **Never** hallucinate dataset IDs. Use `list_datasets` to find them.
3.  **Self-Heal**: If a tool fails, analyze the error and retry with corrected parameters. Do not give up immediately.
4.  **Formatting**: Output Python code in markdown blocks ` ```python ... ``` `.
"""

def load_skill(name: str) -> str:
    path = os.path.join(os.path.dirname(__file__), "skills", f"{name}.md")
    if os.path.exists(path):
        with open(path, "r") as f:
            return f.read()
    return ""

def get_relevant_skills(user_message: str) -> str:
    """
    Simple keyword-based routing.
    In a more advanced system, use embedding similarity.
    """
    skills = []
    msg = user_message.lower()

    if "analyze" in msg or "market" in msg:
        skills.append(load_skill("market_analysis"))

    if "strategy" in msg or "code" in msg or "create" in msg:
        skills.append(load_skill("coding"))

    if "fix" in msg or "error" in msg or "debug" in msg:
        skills.append(load_skill("debugging"))

    # Default to all if unclear? Or just coding/debugging as they are core.
    if not skills:
        skills.append(load_skill("coding"))
        skills.append(load_skill("debugging"))

    return "\n\n".join(skills)

class AIAgent:
    def __init__(self):
        self.client = AIClient() # Client now self-configures via Manager
        self.tools = AITools()
        self.store = ChatStore()
        self.brain = Brain(self.client, self.tools)
        self.job_manager = JobManager()
        self.config_manager = AIConfigManager()

    # Config delegation
    def update_config(self, api_key: str, base_url: str, model: str):
        # Legacy support: update default provider
        self.config_manager.add_provider("Default", base_url, api_key)
        self.config_manager.set_active("default", model)

    async def get_available_models(self) -> List[str]:
        return await self.client.list_models()

    async def chat(self, user_message: str, session_id: str = None, on_status: Callable[[str, str], Awaitable[None]] = None) -> str:
        """
        Main chat loop using the Brain.
        """
        if not session_id:
            session_id = self.store.create_session(title=user_message[:50])

        self.job_manager.start_job(session_id, user_message)

        history = self.store.get_history(session_id)
        job_context = self.job_manager.get_job_context(session_id)

        # Dynamic Skill Injection
        relevant_skills = get_relevant_skills(user_message)
        system_prompt = f"{BASE_PROMPT}\n\n## RELEVANT SKILLS\n{relevant_skills}\n\n{job_context}"

        context = [{"role": "system", "content": system_prompt}] + history[-20:]

        new_user_msg = {"role": "user", "content": user_message}
        context.append(new_user_msg)
        self.store.add_message(session_id, new_user_msg)
        
        # Define Callbacks
        async def on_message(msg: Dict[str, Any]):
            self.store.add_message(session_id, msg)

        async def on_tool_success(name: str, args: Dict, result: Any):
            if name == "create_strategy":
                 self.job_manager.update_job(session_id, "Strategy Created", {"strategy_name": args.get("name")})
            elif name == "run_backtest":
                 self.job_manager.update_job(session_id, "Backtest Run", {"backtest_status": "Complete"})
            elif name == "list_datasets":
                 self.job_manager.update_job(session_id, "Datasets Listed")

        try:
            response = await self.brain.think(
                history=context,
                max_steps=10,
                on_status=on_status,
                on_message=on_message,
                on_tool_success=on_tool_success
            )
            
            self.job_manager.complete_job(session_id)
            return response

        except Exception as e:
            logger.error(f"Agent Chat Error: {e}")
            traceback.print_exc()
            return f"Error: {str(e)}"

    # Proxy methods
    def create_session(self, title: str): return self.store.create_session(title)
    def list_sessions(self): return self.store.list_sessions()
    def get_history(self, sid: str): return self.store.get_history(sid)
    def delete_session(self, sid: str): self.store.delete_session(sid)
