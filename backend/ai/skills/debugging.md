# Debugging & Self-Correction Skill

**Goal**: Identify and fix runtime errors in strategy code or data processing.

## Common Errors & Fixes

### 1. `KeyError: 'datetime'` or `KeyError: 'Date'`
*   **Cause**: Column names are mismatched.
*   **Fix**: QLM standardizes columns to **lowercase**: `open`, `high`, `low`, `close`, `volume`, `datetime`.
*   **Action**: Check `df.columns` or blindly rename: `df.rename(columns=str.lower, inplace=True)`.

### 2. `ValueError: cannot convert float NaN to integer`
*   **Cause**: Trying to convert a Series with `NaN`s to int (e.g. timeframe detection).
*   **Fix**: Use `.fillna(0)` before conversion or drop NaNs.

### 3. Strategy Logic Errors
*   **Issue**: `entry_long` returns empty or all False.
*   **Check**:
    *   Are you comparing compatible types? (Series vs Float).
    *   Are indicators calculating correctly? (Print `vars['sma'].head()`).
    *   Is there enough data? (If dataset < window size, result is all NaN).

### 4. Backtest "No Trades"
*   **Cause**: Strict logic or bad data.
*   **Fix**:
    *   Relax conditions (e.g. `rsi < 30` -> `rsi < 40`).
    *   Check if `risk_model` is returning valid `sl`/`tp`.
    *   Ensure `entry_long` and `entry_short` are not both True (conflict).

## Debugging Workflow
1.  **Read Traceback**: Identify the File and Line Number.
2.  **Isolate Component**: Is it the *Indicator Calculation* or the *Signal Logic*?
3.  **Synthesize Fix**: Rewrite the specific method. Do not rewrite the whole file unless necessary.
