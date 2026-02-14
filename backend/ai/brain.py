from typing import List, Dict, Any, Callable, Awaitable
from backend.ai.client import AIClient
from backend.ai.tools import AITools
import logging
import json

logger = logging.getLogger("QLM.AI.Brain")

class Brain:
    """
    Implements a ReAct (Reasoning + Acting) loop for the AI Agent.
    Allows for multi-step planning and tool execution.
    """
    def __init__(self, client: AIClient, tools: AITools):
        self.client = client
        self.tools = tools
        self.max_steps = 5

    async def think(self, history: List[Dict[str, str]], on_status: Callable[[str, str], Awaitable[None]] = None) -> str:
        """
        Execute the reasoning loop.
        on_status: async func(step_name, detail)
        """
        steps = 0
        current_history = history.copy()

        while steps < self.max_steps:
            logger.info(f"Thinking Step {steps + 1}/{self.max_steps}")
            if on_status:
                await on_status("Thinking", f"Reasoning step {steps + 1}...")

            # 1. Get LLM Response
            response = await self.client.chat_completion(
                messages=current_history,
                tools=self.tools.get_definitions()
            )

            choice = response['choices'][0]
            message = choice['message']

            # If no tool calls, we are done
            if not message.get('tool_calls'):
                return message['content']

            # Add assistant message to history (the "Action")
            current_history.append(message)

            # 2. Execute Tools
            tool_calls = message['tool_calls']
            for tool_call in tool_calls:
                fn_name = tool_call['function']['name']
                fn_args_str = tool_call['function']['arguments']
                fn_args = json.loads(fn_args_str)

                logger.info(f"Brain executing: {fn_name}")
                if on_status:
                    await on_status("Executing Tool", f"{fn_name}")

                tool_result = await self.tools.execute(fn_name, fn_args)

                # Add result to history (the "Observation")
                current_history.append({
                    "role": "tool",
                    "tool_call_id": tool_call['id'],
                    "name": fn_name,
                    "content": json.dumps(tool_result, default=str)
                })

            steps += 1

        return "I've reached my maximum reasoning steps. Here is what I found so far."
