# Debugging & Self-Healing Skill
**Goal**: Fix validation or runtime errors.

## Auto-Fix Protocol
-   If `validate_strategy` returns `valid: False` or a runtime error:
    1.  **Read** the error message carefully.
    2.  **Locate** the fault in the code (e.g., `KeyError` -> missing column, `SyntaxError` -> typo).
    3.  **Rewrite** the strategy using `create_strategy` with the fix applied.
    4.  **Re-validate** immediately.
-   Do not ask the user for permission to fix syntax errors; just fix them.
