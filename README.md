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
*   **Capabilities**:
    *   **Tools**: Access to `create_strategy`, `run_backtest`, `analyze_market`, and more.
    *   **Resources**: Read access to Strategies (`qlm://strategy/...`) and Datasets (`qlm://data/...`).
    *   **Prompts**: Built-in "Senior Quant" persona.

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

### 🖥️ "Financial Terminal" UI
*   **Modern Design**: Dark-themed, Slate/Zinc aesthetics using **Tailwind CSS**.
*   **Mobile Responsive**: Fully functional on desktop and mobile devices.

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

To connect an MCP Client (like Claude Desktop) to QLM:

1.  Start QLM (`python -m backend.main`).
2.  Configure your client:
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
    *(Note: If using `mcp-cli` or similar, point to the SSE endpoint).*

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
