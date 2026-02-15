from typing import List, Dict, Any, Callable, Awaitable, Optional
from backend.ai.client import AIClient
from backend.ai.tools import AITools
import logging
import json
import traceback

logger = logging.getLogger("QLM.AI.Brain")

class Brain:
    """
    Implements a ReAct (Reasoning + Acting) loop for the AI Agent.
    Allows for multi-step planning and tool execution.
    """
    def __init__(self, client: AIClient, tools: AITools):
        self.client = client
        self.tools = tools

    async def think(self,
                    history: List[Dict[str, Any]],
                    max_steps: int = 10,
                    on_status: Callable[[str, str], Awaitable[None]] = None,
                    on_message: Callable[[Dict[str, Any]], Awaitable[None]] = None,
                    on_tool_success: Callable[[str, Dict, Any], Awaitable[None]] = None
                    ) -> str:
        """
        Execute the reasoning loop.

        Args:
            history: The conversation history so far.
            max_steps: Maximum reasoning steps (LLM calls) to prevent infinite loops.
            on_status: Async callback(step_name, detail) for UI updates.
            on_message: Async callback(message) to persist new messages (tool calls, outputs).
            on_tool_success: Async callback(name, args, result) for side effects (e.g. Job updates).
        """
        steps = 0
        current_history = history.copy()

        while steps < max_steps:
            logger.info(f"Thinking Step {steps + 1}/{max_steps}")
            if on_status:
                await on_status("Thinking", f"Step {steps + 1}: Reasoning...")

            # 1. Get LLM Response
            try:
                response = await self.client.chat_completion(
                    messages=current_history,
                    tools=self.tools.get_definitions()
                )
            except Exception as e:
                logger.error(f"LLM Call Failed: {e}")
                traceback.print_exc()
                return f"Error contacting AI provider: {str(e)}"

            choice = response['choices'][0]
            message = choice['message']

            # Add assistant message to local history
            current_history.append(message)

            # Persist assistant message (includes content and/or tool_calls)
            if on_message:
                await on_message(message)

            # If no tool calls, we are done
            if not message.get('tool_calls'):
                return message['content']

            # 2. Execute Tools
            tool_calls = message['tool_calls']
            for tool_call in tool_calls:
                fn_name = tool_call['function']['name']
                fn_args_str = tool_call['function']['arguments']

                # UI Status Update
                if on_status:
                    try:
                        args_disp = json.loads(fn_args_str)
                        disp_str = f"{fn_name}({str(args_disp)[:40]}...)"
                    except:
                        disp_str = f"{fn_name}(...)"
                    await on_status("Invoking Tool", disp_str)

                # Execute
                tool_result = {}
                fn_args = {}
                try:
                    fn_args = json.loads(fn_args_str)
                    logger.info(f"Brain executing: {fn_name} with {fn_args.keys()}")

                    tool_result = await self.tools.execute(fn_name, fn_args)

                    # Check for logical errors in tool result
                    if isinstance(tool_result, dict) and tool_result.get("error"):
                        logger.warning(f"Tool {fn_name} logical error: {tool_result['error']}")
                    else:
                         # Tool Success Callback (Side Effects)
                         if on_tool_success:
                             await on_tool_success(fn_name, fn_args, tool_result)

                except Exception as e:
                    tool_result = {"error": f"Tool Crash: {str(e)}"}
                    logger.error(f"Tool {fn_name} crash: {e}")
                    traceback.print_exc()

                # Create Tool Message
                tool_msg = {
                    "role": "tool",
                    "tool_call_id": tool_call['id'],
                    "name": fn_name,
                    "content": json.dumps(tool_result, default=str)
                }

                # Add to history
                current_history.append(tool_msg)

                # Persist Tool Message
                if on_message:
                    await on_message(tool_msg)

            steps += 1

        return "I reached the maximum reasoning steps (10). I may be stuck in a loop."
