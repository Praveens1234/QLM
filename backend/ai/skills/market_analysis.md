# Market Analysis Skill
**Goal**: Understand market regime (Trend, Volatility, S/R).

## Process
1.  Call `analyze_market_structure(symbol, timeframe)`.
2.  Interpret `trend` (Bullish/Bearish), `volatility_pct` (High/Low), and `rsi`.
3.  **Rule**: If volatility < 0.5%, avoid Breakout strategies. If Trend is weak, prefer Mean Reversion.
