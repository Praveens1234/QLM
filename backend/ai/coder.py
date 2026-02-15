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

ROBUSTNESS RULES:
- **Check Data Length**: In `define_variables`, strictly check if `len(df) < window_size` and return empty/NaN series if so to avoid `IndexError`.
- **Handle NaNs**: Use `.fillna(False)` for boolean signals. Use `.bfill()` or `.ffill()` for indicators where appropriate.
- **Vectorization**: Do NOT use `df.iloc` in vectorized methods. Use `shift()` for previous values.
- **Imports**: `import pandas as pd`, `import numpy as np`, `from typing import Dict, Any`, `from backend.core.strategy import Strategy`.

Output ONLY the Python code block. No markdown chatter.
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
