# Market Analysis Skill

**Goal**: Analyze market structure to determine the optimal strategy regime (Trend vs. Mean Reversion).

## 1. Analysis Workflow
When asked to "Analyze [Symbol]", follow this process:

### Step 1: Trend Identification
*   **Metric**: Price vs. 200-period SMA.
*   **Logic**:
    *   Price > SMA200 + Rising Slope = **Bullish Trend**
    *   Price < SMA200 + Falling Slope = **Bearish Trend**
    *   Flat SMA200 = **Ranging / Consolidation**

### Step 2: Volatility Assessment
*   **Metric**: ATR (Average True Range) % relative to price.
*   **Logic**:
    *   ATR < 0.5% = **Low Volatility** (Expect Breakouts or Squeeze)
    *   ATR > 2.0% = **High Volatility** (Wide stops needed, risk management crucial)

### Step 3: Support & Resistance
*   Identify recent Swing Highs and Lows (local max/min over last 20-50 candles).
*   Are we near a key level?

## 2. Strategy Recommendation Map
Based on the analysis, suggest the right strategy type:

| Market Condition | Recommended Strategy | Risk Profile |
| :--- | :--- | :--- |
| **Strong Trend + Low Volatility** | Trend Following (SMA Crossover, Turtle) | Low Risk, High Reward |
| **Ranging + High Volatility** | Mean Reversion (Bollinger Bands, RSI) | Medium Risk (Catching knives) |
| **Breakout (Key Level + Squeeze)** | Volatility Breakout (Donchian, ATR Break) | High False Signal Rate |

## 3. Output Template
```markdown
### Market Analysis: [Symbol] [Timeframe]

**1. Structure**: [Bullish/Bearish/Neutral]
   - Price is [Above/Below] the 200 SMA.
   - RSI is [Overbought/Oversold/Neutral] at [Value].

**2. Volatility**: [High/Low/Normal]
   - ATR is [Value], indicating [Tight/Wide] price action.

**3. Key Levels**:
   - Support: [Price]
   - Resistance: [Price]

**4. Conclusion**:
   The market is in a [Trend/Range]. I recommend a [Strategy Type] strategy.
```
