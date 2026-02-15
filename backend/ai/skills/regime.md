# Market Regime Classification
**Goal**: Classify market conditions.

## Process
1.  Call `analyze_market_structure`.
2.  Classification Logic:
    -   **Trending Bullish**: SMA50 > SMA200 AND Price > SMA50.
    -   **Trending Bearish**: SMA50 < SMA200 AND Price < SMA50.
    -   **Mean Reverting / Range**: Price within 2% of SMA50 OR SMA50/SMA200 slope is flat.
    -   **High Volatility**: ATR > 2x average.
3.  **Output**: Return a string regime tag (e.g., "Bullish Trend - Low Volatility").
