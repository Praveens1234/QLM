import logging
import json
import traceback
from typing import List, Dict, Any, Optional
from backend.ai.client import AIClient
from backend.ai.tools import AITools
from backend.ai.store import ChatStore

logger = logging.getLogger("QLM.AI.Agent")

SYSTEM_PROMPT = """
You are a Quantitative Trading Assistant for the QLM Framework.
Your goal is to help users develop, validate, and backtest trading strategies.

You have access to the following tools:
- list_datasets: detailed info on available data.
- list_strategies: what strategies imply exist.
- get_strategy_code: read the code of a specific strategy.
- create_strategy: write (or overwrite) a strategy. ALWAYS use purely defined variables, entry_long, entry_short, risk_model, exit (interface compliance).
- validate_strategy: check code before saving.
- run_backtest: execute a strategy on data and get metrics.
- get_market_data: fetch sample market data for analysis.
- read_file: read files within the strategies/logs directories.
- write_file: write/edit files within the strategies/logs directories (use with caution).
- delete_entity: delete datasets or strategies.

Rules:
1. When asked to write a strategy, ALWAYS validate it first or at least mention you are creating it.
2. Use valid Python code compatible with the QLM Strategy Interface.
3. If a backtest fails, analyze the error and propose a fix.
4. Be concise and professional.
5. If you modify a strategy, explain what you changed.
"""

import os

class AIAgent:
    def __init__(self):
        self.client = AIClient()
        self.tools = AITools()
        self.store = ChatStore()

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

    async def chat(self, user_message: str, session_id: str = None) -> str:
        """
        Main chat loop with persistence.
        If session_id is None, creates a new one.
        """
        if not session_id:
            session_id = self.store.create_session(title=user_message[:50])

        # Retrieve history
        history = self.store.get_history(session_id)

        # If new session, prepend system prompt
        if not history:
             history = [{"role": "system", "content": SYSTEM_PROMPT}]
             # We don't necessarily need to save system prompt to DB history unless we want it visible/editable?
             # Usually standard practice is to keep it ephemeral or first message.
             # Let's keep it ephemeral for now, but include it in context.
        else:
             # Prepend system prompt to context sent to LLM, but don't duplicate in DB
             history = [{"role": "system", "content": SYSTEM_PROMPT}] + history

        # Add user message
        new_user_msg = {"role": "user", "content": user_message}
        history.append(new_user_msg)
        self.store.add_message(session_id, new_user_msg)
        
        try:
            # 1. Get initial response from LLM
            response = await self.client.chat_completion(
                messages=history,
                tools=self.tools.get_definitions()
            )
            
            choice = response['choices'][0]
            message = choice['message']
            
            # Save assistant response/call to history
            # Normalize message for storage (remove None values if possible to save space? or just store as is)
            # The client returns dict usually.

            # If plain text response
            if not message.get('tool_calls'):
                self.store.add_message(session_id, message)
                return message['content']
                
            # If tool calls
            self.store.add_message(session_id, message)
            history.append(message) # Add to context for next turn
            
            tool_calls = message['tool_calls']
            for tool_call in tool_calls:
                fn_name = tool_call['function']['name']
                fn_args_str = tool_call['function']['arguments']
                fn_args = json.loads(fn_args_str)
                
                # Execute tool
                logger.info(f"AI calling tool: {fn_name}")
                tool_result = await self.tools.execute(fn_name, fn_args)
                
                # Create tool result message
                tool_msg = {
                    "role": "tool",
                    "tool_call_id": tool_call['id'],
                    "name": fn_name,
                    "content": json.dumps(tool_result, default=str)
                }

                # Add to history and DB
                history.append(tool_msg)
                self.store.add_message(session_id, tool_msg)
                
            # 2. Get final response after tool outputs
            final_response = await self.client.chat_completion(
                messages=history,
                tools=self.tools.get_definitions() 
            )
            
            final_choice = final_response['choices'][0]
            final_message = final_choice['message']

            self.store.add_message(session_id, final_message)
            
            return final_message['content']
            
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
