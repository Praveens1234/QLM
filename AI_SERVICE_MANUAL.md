# AI Services Architecture Manual

## Overview
QLM's AI Service is a modular, provider-agnostic system designed to support OpenAI, Anthropic, and local LLMs (via Ollama/vLLM) interchangeably.

## Key Components

### 1. Unified Client (`backend/ai/client.py`)
*   **Role**: Main entry point for all AI interactions.
*   **Routing**: Dynamically routes requests to the active provider configured in `config.json` (persisted in SQLite).
*   **Resilience**: Automatically retries failed requests using exponential backoff.

### 2. Provider Architecture (`backend/ai/providers/`)
*   **BaseProvider**: Abstract interface defining `chat_completion` and `list_models`.
*   **OpenAIProvider**: Handles OpenAI and compatible endpoints.
*   **AnthropicProvider**: Adapts messages to Claude's format.
*   **GenericProvider**: Optimized for local LLMs (less strict validation).

### 3. Configuration & Security (`backend/ai/config_manager.py`)
*   **Storage**: SQLite (`data/qlm.db`).
*   **Security**: API Keys are masked in API responses (`***`).
*   **Models**: Pydantic models in `backend/ai/models.py` enforce strict typing.

### 4. Skill System (`backend/ai/skills/`)
*   **Registry**: Loads markdown files from `backend/ai/skills/`.
*   **Metadata**: Supports YAML frontmatter for tags and descriptions.
*   **Dynamic Injection**: The Agent automatically selects relevant skills based on user queries.

---

## How-To Guides

### Adding a New Provider
1.  Navigate to **Settings > AI Providers**.
2.  Click **"Add Provider"**.
3.  Select Type (e.g., "Generic" for Ollama).
4.  Enter Base URL (e.g., `http://localhost:11434/v1`).
5.  (Optional) Enter API Key.
6.  The system will auto-discover available models.

### Adding a New Skill
1.  Create a markdown file in `backend/ai/skills/`.
2.  Add YAML frontmatter:
    ```markdown
    ---
    name: My Custom Skill
    description: Explains how to trade volatility.
    tags: [volatility, options, risk]
    ---

    # Skill Content
    Here is how you trade volatility...
    ```
3.  The agent will now index this skill.

### Switching Models
*   Use the **Global Settings** API (`POST /api/settings/ai/config/active`) or the Dashboard UI.
*   The `UnifiedClient` immediately switches traffic to the new model.

## Troubleshooting
*   **Logs**: Check `logs/qlm.log` for provider errors.
*   **Crashes**: Critical failures dump forensics to `logs/crashes/`.
*   **Rate Limits**: The system automatically retries 429 errors.
