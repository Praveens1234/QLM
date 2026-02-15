import logging
import json
import traceback
from typing import List, Dict, Any, Optional, Callable, Awaitable
from backend.ai.client import AIClient
from backend.ai.tools import AITools
from backend.ai.store import ChatStore
from backend.ai.brain import Brain
from backend.ai.memory import JobManager
import os

logger = logging.getLogger("QLM.AI.Agent")

# Dynamic System Prompt Loader
def load_system_prompt():
    base_prompt = """
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
    # Load Skills
    skills_path = os.path.join(os.path.dirname(__file__), "SKILLS.md")
    if os.path.exists(skills_path):
        with open(skills_path, "r") as f:
            skills = f.read()
            base_prompt += f"\n\n{skills}"

    return base_prompt

class AIAgent:
    def __init__(self):
        self.client = AIClient()
        self.tools = AITools()
        self.store = ChatStore()
        self.brain = Brain(self.client, self.tools)
        self.job_manager = JobManager()

        self.config_path = os.path.join(os.path.dirname(__file__), "config.json")
        self._load_config()
        self.system_prompt = load_system_prompt()
        
    def _load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    self.client.configure(
                        config.get("api_key"), 
                        config.get("base_url", "https://api.openai.com/v1"), 
                        config.get("model", "gpt-4-turbo")
                    )
            except Exception as e:
                logger.error(f"Failed to load config: {e}")

    def update_config(self, api_key: str, base_url: str, model: str):
        self.client.configure(api_key, base_url, model)
        # Update config file... (omitted for brevity, same as before)

    async def get_available_models(self) -> List[str]:
        return await self.client.list_models()

    async def chat(self, user_message: str, session_id: str = None, on_status: Callable[[str, str], Awaitable[None]] = None) -> str:
        """
        Main chat loop using the Brain.
        """
        if not session_id:
            session_id = self.store.create_session(title=user_message[:50])

        # Job Management: Check if this is a new goal
        # For simplicity, treat every user message as a potential goal update or query
        self.job_manager.start_job(session_id, user_message) # Reset job context for new turn

        history = self.store.get_history(session_id)
        job_context = self.job_manager.get_job_context(session_id)

        # Context Management: Summarization could go here if history > limit
        # For now, simple truncation or full context
        context = [{"role": "system", "content": self.system_prompt + "\n" + job_context}] + history[-20:] # Keep last 20 turns

        new_user_msg = {"role": "user", "content": user_message}
        context.append(new_user_msg)
        self.store.add_message(session_id, new_user_msg)
        
        try:
            steps = 0
            max_steps = 10 # Robust limit

            while steps < max_steps:
                if on_status:
                    await on_status("Thinking", f"Step {steps+1}: Reasoning...")

                response = await self.client.chat_completion(
                    messages=context,
                    tools=self.tools.get_definitions()
                )
                
                choice = response['choices'][0]
                message = choice['message']
                
                # Save assistant thought/action
                self.store.add_message(session_id, message)
                context.append(message)
                
                if not message.get('tool_calls'):
                    self.job_manager.complete_job(session_id)
                    return message['content'] # Final Answer

                # Execute Tools
                tool_calls = message['tool_calls']
                for tool_call in tool_calls:
                    fn_name = tool_call['function']['name']
                    fn_args_str = tool_call['function']['arguments']

                    # Status Update
                    if on_status:
                        # Parse for display
                        try:
                            args_disp = json.loads(fn_args_str)
                            disp_str = f"{fn_name}({str(args_disp)[:40]}...)"
                        except:
                            disp_str = f"{fn_name}(...)"
                        await on_status("Invoking Tool", disp_str)

                    # Execute
                    tool_result = {}
                    try:
                        fn_args = json.loads(fn_args_str)
                        tool_result = await self.tools.execute(fn_name, fn_args)

                        # Job Updates based on tool
                        if fn_name == "create_strategy":
                            self.job_manager.update_job(session_id, "Strategy Created", {"strategy_name": fn_args.get("name")})
                        elif fn_name == "run_backtest":
                            self.job_manager.update_job(session_id, "Backtest Run", {"backtest_status": "Complete"})
                        elif fn_name == "list_datasets":
                             self.job_manager.update_job(session_id, "Datasets Listed")

                        # Handle Logical Errors (Soft Fail)
                        if isinstance(tool_result, dict) and tool_result.get("error"):
                            logger.warning(f"Tool {fn_name} logical error: {tool_result['error']}")

                            # AUTO-FIX Prompt Injection (if applicable)
                            if "validate" in fn_name or "create" in fn_name:
                                # Start of Auto-Fix loop
                                pass

                    except Exception as e:
                        # Crash (Hard Fail) -> Convert to Soft Fail for AI
                        tool_result = {"error": f"Tool Crash: {str(e)}"}
                        logger.error(f"Tool {fn_name} crash: {e}")

                    result_str = json.dumps(tool_result, default=str)

                    tool_msg = {
                        "role": "tool",
                        "tool_call_id": tool_call['id'],
                        "name": fn_name,
                        "content": result_str
                    }

                    self.store.add_message(session_id, tool_msg)
                    context.append(tool_msg)

                steps += 1
            
            return "I reached the maximum reasoning steps (10). I may be stuck in a loop."

        except Exception as e:
            logger.error(f"Agent Chat Error: {e}")
            traceback.print_exc()
            return f"Error: {str(e)}"

    # Proxy methods
    def create_session(self, title: str): return self.store.create_session(title)
    def list_sessions(self): return self.store.list_sessions()
    def get_history(self, sid: str): return self.store.get_history(sid)
    def delete_session(self, sid: str): self.store.delete_session(sid)
