import os
import yaml
import logging
from typing import List, Dict, Optional
from mcp.types import Prompt, PromptMessage, TextContent, GetPromptResult

logger = logging.getLogger("QLM.AI.Prompts")

class PromptManager:
    """
    Loads and manages dynamic MCP prompts from YAML templates.
    """
    def __init__(self, prompt_dir: str = "backend/ai/prompts"):
        self.prompt_dir = prompt_dir
        if not os.path.exists(prompt_dir):
            os.makedirs(prompt_dir)
        self.prompts: Dict[str, Dict] = {}
        self._load_prompts()

    def _load_prompts(self):
        self.prompts.clear()
        for filename in os.listdir(self.prompt_dir):
            if filename.endswith(".yaml") or filename.endswith(".yml"):
                try:
                    with open(os.path.join(self.prompt_dir, filename), "r") as f:
                        data = yaml.safe_load(f)
                        if "name" in data:
                            self.prompts[data["name"]] = data
                except Exception as e:
                    logger.error(f"Failed to load prompt {filename}: {e}")

    def list_prompts(self) -> List[Prompt]:
        # Refresh on list (dev mode friendly)
        self._load_prompts()
        result = []
        for name, data in self.prompts.items():
            result.append(Prompt(
                name=name,
                description=data.get("description", ""),
                arguments=[] # Logic for args not yet implemented in YAML schema
            ))
        return result

    def get_prompt(self, name: str, arguments: Dict = None) -> GetPromptResult:
        if name not in self.prompts:
            raise ValueError(f"Prompt {name} not found")

        data = self.prompts[name]
        messages = []

        # Simple string replacement for args
        args = arguments or {}

        for msg in data.get("messages", []):
            content = msg.get("content", "")
            # Inject variables
            for k, v in args.items():
                content = content.replace(f"{{{{{k}}}}}", str(v))

            messages.append(PromptMessage(
                role=msg.get("role", "user"),
                content=TextContent(type="text", text=content)
            ))

        return GetPromptResult(messages=messages)

# Singleton
prompt_manager = PromptManager()
