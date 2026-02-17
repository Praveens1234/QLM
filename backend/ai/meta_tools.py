import asyncio
import logging
from typing import Dict, Any, List
from backend.ai.tools import AITools

logger = logging.getLogger("QLM.AI.MetaTools")

class MetaToolRegistry:
    """
    Registry for 'Macro Tools' that compose multiple atomic tools.
    """
    def __init__(self, ai_tools: AITools):
        self.ai_tools = ai_tools

    async def execute(self, tool_name: str, args: Dict) -> Any:
        if tool_name == "full_audit":
            return await self._full_audit(args)
        raise ValueError(f"Meta-tool {tool_name} not found")

    async def _full_audit(self, args: Dict) -> Dict:
        """
        Full Audit: List Strategies -> Validate All -> Report.
        """
        results = {}

        # 1. List
        strats = await self.ai_tools.execute("list_strategies", {})
        results["strategies_found"] = len(strats)

        audit_log = []

        # 2. Validate Each
        for s in strats:
            name = s['name']
            code_res = await self.ai_tools.execute("get_strategy_code", {"name": name})
            if code_res.get("found"):
                val_res = await self.ai_tools.execute("validate_strategy", {"code": code_res['code']})
                audit_log.append({
                    "strategy": name,
                    "valid": val_res.get("valid"),
                    "error": val_res.get("error")
                })

        results["audit_details"] = audit_log
        return results

    def get_definitions(self) -> List[Dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "full_audit",
                    "description": "Meta-Tool: Scans all strategies and validates them.",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        ]
