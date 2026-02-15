# Strategy Explanation
**Goal**: Explain strategy logic in plain English.

## Process
1.  Call `get_strategy_code(name)`.
2.  Analyze `entry_long`, `entry_short`, `exit`, `risk_model`.
3.  **Output**: A summary report covering:
    -   **Entry Logic**: "Enters long when MACD crosses above Signal..."
    -   **Risk**: "Uses 2x ATR for Stop Loss."
    -   **Suitability**: "Best for trending markets."
