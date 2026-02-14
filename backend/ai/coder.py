from backend.ai.client import AIClient
import re

CODER_PROMPT = """
You are an Expert Python Strategy Developer for the QLM Framework.
Your ONLY task is to write high-quality, bug-free Python code for trading strategies.

INTERFACE REQUIREMENTS:
1. Class must inherit from `backend.core.strategy.Strategy`.
2. Must implement:
   - `define_variables(self, df: pd.DataFrame) -> Dict[str, pd.Series]`
   - `entry_long(self, df: pd.DataFrame, vars: Dict[str, pd.Series]) -> pd.Series` (boolean)
   - `entry_short(self, df: pd.DataFrame, vars: Dict[str, pd.Series]) -> pd.Series` (boolean)
   - `risk_model(self, df: pd.DataFrame, vars: Dict[str, pd.Series]) -> Dict[str, pd.Series]` (keys: 'sl', 'tp')
   - `exit(self, df: pd.DataFrame, vars: Dict[str, pd.Series], trade: Dict[str, Any]) -> bool`
   - `position_size(self, df: pd.DataFrame, vars: Dict[str, pd.Series]) -> pd.Series` (optional, default 1.0)

RULES:
- Do NOT use `df.iloc` in vectorized methods (`define_variables`, `entry_*`). Use `shift()` for previous values.
- `entry_long` and `entry_short` MUST return boolean Series.
- Handle NaNs explicitly (e.g., `fillna(False)` for signals).
- Imports allowed: `pandas`, `numpy`, `typing`, `backend.core.strategy.Strategy`.
- Output ONLY the Python code block. No markdown chatter.
"""

class AutoCoder:
    def __init__(self, client: AIClient):
        self.client = client

    async def generate_code(self, description: str) -> str:
        messages = [
            {"role": "system", "content": CODER_PROMPT},
            {"role": "user", "content": f"Write a strategy code for: {description}"}
        ]

        response = await self.client.chat_completion(messages=messages)
        content = response['choices'][0]['message']['content']

        # Extract code block if wrapped in markdown
        match = re.search(r"```python\n(.*?)\n```", content, re.DOTALL)
        if match:
            return match.group(1)
        return content
