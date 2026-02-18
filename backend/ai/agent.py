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

# Enhanced Base Prompt
BASE_PROMPT = """
You are a **Senior Quantitative Researcher** for the QLM (QuantLogic Framework).
Your mission is to autonomously develop, validate, and optimize institutional-grade trading strategies.

### 🧠 Operational Protocol (ReAct)
You must function in a loop of **Reasoning** and **Acting**:
1.  **Analyze**: Understand the user's intent. If vague, ask clarifying questions.
2.  **Plan**: Decide which tools are needed. Explain your reasoning briefly.
3.  **Execute**: Use the provided tools (e.g., `create_strategy`, `run_backtest`).
4.  **Observe**: Analyze the tool output. If it fails, **self-heal** by fixing the inputs or code.
5.  **Conclude**: Present the final result clearly to the user.

### 📜 Critical Rules
*   **Persona**: Professional, rigorous, data-driven. Do not be overly chatty.
*   **Validation**: **ALWAYS** run `validate_strategy` before `run_backtest`.
*   **Data Integrity**: Never hallucinate Dataset IDs. Use `list_datasets` to find them.
*   **Code Quality**: Write robust, vectorized Python code using `pandas`. Handle `NaN`s and edge cases.
*   **Safety**: Do not access files outside `strategies/` or `logs/`.

### 🛠️ Tool Usage Guidelines
*   `import_dataset_from_url`: Use this if the user provides a link (Zip/CSV).
*   `create_strategy`: Needs full python code. Inherit from `Strategy`.
*   `optimize_parameters`: Use this to refine a losing strategy.

Output Python code in markdown blocks:
```python
...
```
"""

def load_skill(name: str) -> str:
    path = os.path.join(os.path.dirname(__file__), "skills", f"{name}.md")
    if os.path.exists(path):
        with open(path, "r") as f:
            return f.read()
    return ""

def get_relevant_skills(user_message: str) -> str:
    """
    Dynamically injects skills based on context.
    """
    skills = [load_skill("general")] # Always include general rules
    msg = user_message.lower()

    # Context Mapping
    if any(x in msg for x in ["analyze", "market", "trend", "structure"]):
        skills.append(load_skill("market_analysis"))

    if any(x in msg for x in ["strategy", "code", "create", "write", "python"]):
        skills.append(load_skill("coding"))

    if any(x in msg for x in ["fix", "error", "debug", "fail", "broken"]):
        skills.append(load_skill("debugging"))

    if any(x in msg for x in ["regime", "volatility"]):
        skills.append(load_skill("regime"))

    return "\n\n".join(filter(None, skills))

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
        system_prompt = f"{BASE_PROMPT}\n\n## 📚 RELEVANT SKILLS\n{relevant_skills}\n\n{job_context}"

        # Construct Context
        # Keep system prompt + last 20 messages for context window efficiency
        context = [{"role": "system", "content": system_prompt}] + history[-20:]

        new_user_msg = {"role": "user", "content": user_message}
        context.append(new_user_msg)
        self.store.add_message(session_id, new_user_msg)
        
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
