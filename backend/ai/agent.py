import logging
import json
import traceback
from typing import List, Dict, Any, Optional, Callable, Awaitable
from backend.ai.client import AIClient
from backend.ai.tools import AITools
from backend.ai.store import ChatStore
from backend.ai.brain import Brain
import os

logger = logging.getLogger("QLM.AI.Agent")

SYSTEM_PROMPT = """
You are a Quantitative Trading Assistant for the QLM Framework.
Your goal is to help users develop, validate, and backtest trading strategies.

You have access to advanced tools for analysis, coding, and simulation.
When solving complex problems, use a step-by-step approach (Reasoning Loop):
1. Analyze the request.
2. Gather necessary information (list datasets, read code).
3. Formulate a plan or code solution.
4. Execute and verify (validate code, run backtest).
5. Refine if necessary.

Rules:
1. Always validate strategies before saving.
2. Use valid Python code compatible with QLM.
3. Be concise and professional.
"""

class AIAgent:
    def __init__(self):
        self.client = AIClient()
        self.tools = AITools()
        self.store = ChatStore()
        self.brain = Brain(self.client, self.tools)

        self.config_path = os.path.join(os.path.dirname(__file__), "config.json")
        self._load_config()
        
    def _load_config(self):
        """Load config from disk if exists"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    self.client.configure(
                        config.get("api_key"), 
                        config.get("base_url", "https://api.openai.com/v1"), 
                        config.get("model", "gpt-4-turbo")
                    )
                    logger.info("Loaded AI config from disk.")
            except Exception as e:
                logger.error(f"Failed to load config: {e}")

    def _save_config(self, api_key, base_url, model):
        """Save config to disk"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump({
                    "api_key": api_key,
                    "base_url": base_url,
                    "model": model
                }, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def update_config(self, api_key: str, base_url: str, model: str):
        self.client.configure(api_key, base_url, model)
        self._save_config(api_key, base_url, model)

    async def get_available_models(self) -> List[str]:
        return await self.client.list_models()

    async def chat(self, user_message: str, session_id: str = None, on_status: Callable[[str, str], Awaitable[None]] = None) -> str:
        """
        Main chat loop with persistence and Brain integration.
        on_status: async func(step_name, detail) for real-time feedback
        """
        if not session_id:
            session_id = self.store.create_session(title=user_message[:50])

        # Retrieve history
        history = self.store.get_history(session_id)

        # Context management
        context = [{"role": "system", "content": SYSTEM_PROMPT}] + history

        # Add user message
        new_user_msg = {"role": "user", "content": user_message}
        context.append(new_user_msg)
        self.store.add_message(session_id, new_user_msg)
        
        try:
            # Re-implement loop here to control persistence AND status updates
            current_history = context
            steps = 0
            max_steps = 5
            final_content = ""

            while steps < max_steps:
                if on_status:
                    await on_status("Thinking", f"Step {steps+1}: Consulting AI Model...")

                response = await self.client.chat_completion(
                    messages=current_history,
                    tools=self.tools.get_definitions()
                )
                
                choice = response['choices'][0]
                message = choice['message']
                
                # Save assistant message (Action thought)
                self.store.add_message(session_id, message)
                current_history.append(message)
                
                if not message.get('tool_calls'):
                    final_content = message['content']
                    break

                # Execute tools
                tool_calls = message['tool_calls']
                for tool_call in tool_calls:
                    fn_name = tool_call['function']['name']
                    fn_args_str = tool_call['function']['arguments']
                    fn_args = json.loads(fn_args_str)

                    if on_status:
                        await on_status("Executing Tool", f"Running {fn_name}...")

                    logger.info(f"Agent executing: {fn_name}")
                    tool_result = await self.tools.execute(fn_name, fn_args)

                    tool_msg = {
                        "role": "tool",
                        "tool_call_id": tool_call['id'],
                        "name": fn_name,
                        "content": json.dumps(tool_result, default=str)
                    }

                    self.store.add_message(session_id, tool_msg)
                    current_history.append(tool_msg)

                steps += 1
            
            if not final_content:
                final_content = "I reached my reasoning limit."

            return final_content
            
        except Exception as e:
            logger.error(f"Agent Chat Error: {e}")
            traceback.print_exc()
            return f"Error: {str(e)}"

    def create_session(self, title: str) -> str:
        return self.store.create_session(title)

    def list_sessions(self) -> List[Dict]:
        return self.store.list_sessions()

    def get_history(self, session_id: str) -> List[Dict]:
        return self.store.get_history(session_id)

    def delete_session(self, session_id: str):
        self.store.delete_session(session_id)
