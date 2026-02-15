# Strategy Coding Skill
**Goal**: Write high-performance Python strategy code.

## Standards
-   Inherit from `backend.core.strategy.Strategy`.
-   Use `pandas` vectorization (avoid loops).
-   Implement `risk_model` with dynamic SL/TP (e.g., ATR-based).
-   **Self-Correction**: If you encounter `KeyError` or `NaN` issues, assume data gaps and add `fillna()` or checks.
