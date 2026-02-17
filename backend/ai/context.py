from typing import List, Dict
import logging

logger = logging.getLogger("QLM.AI.Context")

class ContextManager:
    """
    Manages conversation history token usage.
    """

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Rough character-based estimation (4 chars ~= 1 token).
        Fast and doesn't require loading heavy tokenizer libraries.
        """
        return len(text) // 4

    @staticmethod
    def prune_history(history: List[Dict[str, str]], max_tokens: int = 4000) -> List[Dict[str, str]]:
        """
        Retain system prompt, but truncate older messages if limit exceeded.
        """
        if not history: return []

        system_msg = history[0] if history[0]["role"] == "system" else None
        msgs = history[1:] if system_msg else history

        current_tokens = 0
        pruned_msgs = []

        # Traverse backwards
        for msg in reversed(msgs):
            content = str(msg.get("content", ""))
            tokens = ContextManager.estimate_tokens(content)

            if current_tokens + tokens > max_tokens:
                logger.info(f"Context limit reached ({current_tokens} + {tokens} > {max_tokens}). Pruning older messages.")
                break

            current_tokens += tokens
            pruned_msgs.insert(0, msg)

        if system_msg:
            pruned_msgs.insert(0, system_msg)

        return pruned_msgs
