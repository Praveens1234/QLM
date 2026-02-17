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
from backend.ai.prompt_manager import prompt_manager
from backend.ai.skills.registry import skill_registry
from backend.ai.context import ContextManager
import os

logger = logging.getLogger("QLM.AI.Agent")

class AIAgent:
    def __init__(self):
        self.client = AIClient()
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

    def _inject_skills(self, user_message: str) -> str:
        """
        Dynamically selects relevant skills based on user query.
        """
        relevant_skills = skill_registry.search_skills(user_message)

        # Always include 'general' if it exists
        general = skill_registry.get_skill("general")
        if general and general not in relevant_skills:
            relevant_skills.insert(0, general)

        if not relevant_skills:
            return ""

        skill_text = "## 📚 RELEVANT SKILLS\n"
        for skill in relevant_skills:
            skill_text += f"### {skill.name}\n{skill.content}\n\n"

        return skill_text

    async def chat(self, user_message: str, session_id: str = None, on_status: Callable[[str, str], Awaitable[None]] = None) -> str:
        """
        Main chat loop using the Brain.
        """
        if not session_id:
            session_id = self.store.create_session(title=user_message[:50])

        self.job_manager.start_job(session_id, user_message)

        history = self.store.get_history(session_id)
        job_context = self.job_manager.get_job_context(session_id)

        # 1. Load Base Prompt
        prompt_data = prompt_manager.get_prompt("senior_quant")
        base_system_msg = prompt_data.messages[0].content.text # Assuming single system message

        # 2. Inject Dynamic Skills
        skills_section = self._inject_skills(user_message)

        # 3. Assemble System Prompt
        system_prompt = f"{base_system_msg}\n\n{skills_section}\n\n{job_context}"

        # 4. Construct Context with Smart Pruning
        # Get config for max tokens
        config = self.config_manager.get_config()

        # Keep system prompt separate
        raw_history = history + [{"role": "user", "content": user_message}]
        pruned_history = ContextManager.prune_history(raw_history, max_tokens=config.max_tokens)

        context = [{"role": "system", "content": system_prompt}] + pruned_history

        self.store.add_message(session_id, {"role": "user", "content": user_message})
        
        # Define Callbacks
        async def on_message(msg: Dict[str, Any]):
            self.store.add_message(session_id, msg)

        async def on_tool_success(name: str, args: Dict, result: Any):
            # Intelligent Job Updates
            if name == "create_strategy":
                 self.job_manager.update_job(session_id, "Strategy Created", {"strategy_name": args.get("name")})
            elif name == "run_backtest":
                 self.job_manager.update_job(session_id, "Backtest Complete", {"status": "success"})
            elif name == "import_dataset_from_url":
                 self.job_manager.update_job(session_id, "Data Imported", {"id": result.get("id")})
            elif name == "validate_strategy":
                 if result.get("valid"):
                     self.job_manager.update_job(session_id, "Validation Passed")
                 else:
                     self.job_manager.update_job(session_id, "Validation Failed")

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
            return f"**System Error**: {str(e)}"

    # Proxy methods
    def create_session(self, title: str): return self.store.create_session(title)
    def list_sessions(self): return self.store.list_sessions()
    def get_history(self, sid: str): return self.store.get_history(sid)
    def delete_session(self, sid: str): self.store.delete_session(sid)
