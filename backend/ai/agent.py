
import logging
import json
import traceback
from typing import List, Dict, Any, Optional
from backend.ai.client import AIClient
from backend.ai.tools import AITools

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

Rules:
1. When asked to write a strategy, ALWAYS validate it first or at least mention you are creating it.
2. Use valid Python code compatible with the QLM Strategy Interface.
3. If a backtest fails, analyze the error and propose a fix.
4. Be concise and professional.
"""

import os

class AIAgent:
    def __init__(self):
        self.client = AIClient()
        self.tools = AITools()
        self.history: List[Dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
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

    async def chat(self, user_message: str) -> str:
        """
        Main chat loop. Handles tool calls automatically.
        """
        # Add user message to history
        self.history.append({"role": "user", "content": user_message})
        
        try:
            # 1. Get initial response from LLM
            response = await self.client.chat_completion(
                messages=self.history,
                tools=self.tools.get_definitions()
            )
            
            choice = response['choices'][0]
            message = choice['message']
            
            # If plain text response
            if not message.get('tool_calls'):
                self.history.append(message)
                return message['content']
                
            # If tool calls
            self.history.append(message) # Add the assistant's "thought" / call request
            
            tool_calls = message['tool_calls']
            for tool_call in tool_calls:
                fn_name = tool_call['function']['name']
                fn_args_str = tool_call['function']['arguments']
                fn_args = json.loads(fn_args_str)
                
                # Execute tool
                logger.info(f"AI calling tool: {fn_name}")
                tool_result = await self.tools.execute(fn_name, fn_args)
                
                # Add result to history
                self.history.append({
                    "role": "tool",
                    "tool_call_id": tool_call['id'],
                    "name": fn_name,
                    "content": json.dumps(tool_result, default=str)
                })
                
            # 2. Get final response after tool outputs
            final_response = await self.client.chat_completion(
                messages=self.history,
                tools=self.tools.get_definitions() 
            )
            
            final_choice = final_response['choices'][0]
            final_message = final_choice['message']
            self.history.append(final_message)
            
            return final_message['content']
            
        except Exception as e:
            logger.error(f"Agent Chat Error: {e}")
            traceback.print_exc()
            return f"Error: {str(e)}"

    def clear_history(self):
        self.history = [{"role": "system", "content": SYSTEM_PROMPT}]
