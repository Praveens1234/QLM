# 🚀 QuantLogic Framework (QLM)

![QLM Banner](https://img.shields.io/badge/Status-Beta-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.12%2B-yellow?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)
![AI-Powered](https://img.shields.io/badge/AI-Agentic-purple?style=for-the-badge)
![MCP-Ready](https://img.shields.io/badge/MCP-Enabled-orange?style=for-the-badge)

**QuantLogic Framework (QLM)** is an institutional-grade algorithmic trading platform designed for quantitative researchers. It integrates a high-performance **Event-Driven Backtester** with an autonomous **AI Research Agent** capable of self-healing, multi-step reasoning, and full strategy lifecycle management.

Now fully compatible with the **Model Context Protocol (MCP)**, allowing external AI clients (Claude Desktop, Zed, etc.) to control the QLM engine directly.

---

## 📸 Interface Preview

### Desktop Terminal
| **Dashboard** | **AI Architect** |
|:---:|:---:|
| <img src="public/screenshots/01_dashboard.png" width="400" /> | <img src="public/screenshots/05_ai_assistant.png" width="400" /> |

| **Strategy Lab** | **Backtest Runner** |
|:---:|:---:|
| <img src="public/screenshots/03_strategy_lab.png" width="400" /> | <img src="public/screenshots/04_backtest_runner.png" width="400" /> |

### Mobile Responsive
<img src="public/screenshots/06_mobile_dashboard.png" width="200" />

---

## ✨ Key Features

### 🔌 MCP Service (New!)
*   **Protocol**: Exposes QLM via Server-Sent Events (SSE).
*   **Endpoint**: `http://<IP>:8010/api/mcp/sse`
*   **Capabilities**: Full control over Data, Strategies, and Backtesting.

### 🧠 Agentic AI Core
*   **ReAct "Brain" Architecture**: The AI reasons in loops (Thought -> Action -> Observation) to solve complex tasks.
*   **Self-Healing Workflow**: If a tool fails (e.g., syntax error in generated code), the agent analyzes the stack trace and autonomously pushes a fix.
*   **Auto-Coder**: Generates high-quality, bug-free Python strategies strictly adhering to the QLM interface.

### 📊 Professional Data Management
*   **Universal Ingestion**: Local uploads and Direct URL imports (CSV/ZIP).
*   **Parquet Storage**: High-performance columnar storage for million-row datasets.
*   **Market Structure Analytics**: Built-in tools for Trend, Volatility (ATR), and Support/Resistance analysis.

### ⚡ Institutional-Grade Backtesting
*   **Event-Driven Engine**: Simulates realistic market conditions candle-by-candle.
*   **Advanced Metrics**: Max Drawdown (Abs), Profit Factor, Sharpe Ratio, Expectancy.
*   **Position Sizing**: Dynamic sizing logic embedded in strategies.

---

## 🛠️ Installation

### Prerequisites
*   Python 3.12+
*   Git

### Quick Start

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/Praveens1234/QLM.git
    cd QLM
    ```

2.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the Application**
    ```bash
    python -m backend.main
    ```
    Access the terminal at `http://localhost:8010`.

---

## 🚀 MCP Connection Guide

Use any MCP-compliant client (e.g., Claude Desktop, Zed Editor) to connect to QLM.

1.  **Start QLM**: Ensure the server is running on `0.0.0.0:8010`.
2.  **Configure Client**: Add the SSE endpoint.

**Claude Desktop Config (`claude_desktop_config.json`):**
```json
{
  "mcpServers": {
    "qlm": {
      "command": "",
      "url": "http://127.0.0.1:8010/api/mcp/sse"
    }
  }
}
```

### 🧰 MCP Tool Reference

Once connected, you have full control via these tools:

| Tool Name | Description |
| :--- | :--- |
| **`create_strategy`** | Write/Update a Python strategy file. |
| **`validate_strategy`** | Dry-run code validation and syntax check. |
| **`run_backtest`** | Execute a simulation on a specific dataset. |
| **`optimize_parameters`** | Run parameter optimization simulations. |
| **`list_datasets`** | View available OHLCV data. |
| **`import_dataset_from_url`** | Download & ingest CSV/ZIP from a direct link. |
| **`get_market_data`** | Peek at raw data rows (Pandas DataFrame). |
| **`analyze_market_structure`** | Calculate Trend, Volatility, and S/R levels. |
| **`consult_skill`** | Retrieve expert docs (Coding, Analysis, Debugging). |
| **`get_system_status`** | View server health, version, and CPU/RAM usage. |
| **`update_ai_config`** | Change the active AI Model/Provider. |
| **`read_file`** | Read strategy source code or logs. |
| **`write_file`** | Direct file access (Sandboxed). |

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:
1.  Fork the repository.
2.  Create a feature branch (`git checkout -b feature/NewFeature`).
3.  Commit your changes.
4.  Push to the branch.
5.  Open a Pull Request.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Developed with ❤️ by Praveen**
