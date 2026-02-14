# 🚀 QuantLogic Framework (QLM)

![QLM Banner](https://img.shields.io/badge/Status-Beta-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.12%2B-yellow?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)
![AI-Powered](https://img.shields.io/badge/AI-Agentic-purple?style=for-the-badge)

**QuantLogic Framework (QLM)** is a next-generation, high-performance algorithmic trading platform designed for quantitative researchers and traders. It combines a robust **Event-Driven Backtester** with a **State-of-the-Art AI Agent** capable of reasoning, coding, and optimizing strategies autonomously.

---

## ✨ Features

### 🧠 Agentic AI Core
*   **ReAct "Brain" Architecture**: The AI reasons in loops (Thought -> Action -> Observation) to solve complex tasks.
*   **Auto-Coder**: Generates high-quality, bug-free Python strategies strictly adhering to the QLM interface.
*   **Full Control**: The agent can manage datasets, run backtests, analyze market structure, and debug code.
*   **Live Status Pipeline**: Watch the agent "think" and execute tools in real-time via the UI.

### 📊 Professional Data Management
*   **Universal Ingestion**: Drag-and-drop CSV uploads with automatic parsing.
*   **Parquet Storage**: High-performance columnar storage for million-row datasets.
*   **Market Structure Analytics**: Built-in tools for Trend, Volatility (ATR), and Support/Resistance analysis.

### ⚡ Institutional-Grade Backtesting
*   **Event-Driven Engine**: Simulates realistic market conditions candle-by-candle.
*   **Advanced Metrics**: Max Drawdown (Abs), Profit Factor, Sharpe Ratio, Expectancy.
*   **Position Sizing**: Dynamic sizing logic embedded in strategies.
*   **Vectorized & Loop Hybrid**: Optimized for both speed and complex logic.

### 🖥️ "Financial Terminal" UI
*   **Modern Design**: Dark-themed, Glassmorphism aesthetics using **Tailwind CSS**.
*   **Mobile Responsive**: Fully functional on desktop and mobile devices.
*   **Strategy Lab**: Integrated Monaco Editor with "Apply Code" from AI chat.
*   **Real-Time Visualization**: WebSocket-powered progress bars and status updates.

---

## 🛠️ Installation

### Prerequisites
*   Python 3.9+
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
    Access the terminal at `http://localhost:8000`.

---

## 🚀 Usage Guide

### 1. Ingest Data
Navigate to **Data Manager** and upload your OHLCV CSV files.
*   **Format**: `Date, Open, High, Low, Close, Volume`
*   **Processing**: auto-converted to Parquet for speed.

### 2. AI Assistant (The "Brain")
Go to the **AI Assistant** tab.
*   **Ask**: "Analyze XAUUSD 1H structure and write a Trend Following strategy."
*   **Watch**: The "Status Pipeline" will show the agent analyzing data -> planning -> coding.
*   **Apply**: Click **"Apply"** on the generated code block to push it to the Editor.

### 3. Strategy Lab
*   Review and edit the generated Python code.
*   Click **"Validate"** to run a safety check and dry-run simulation.
*   Click **"Save"** to version control your strategy.

### 4. Backtest Runner
*   Select your Dataset and Strategy.
*   Click **"Run Simulation"**.
*   View real-time progress and detailed performance metrics.

---

## 📂 Project Structure

```
QLM/
├── backend/                # FastAPI Application
│   ├── ai/                 # AI Brain, Agent, Tools, Store
│   ├── core/               # Backtest Engine, Strategy Interface
│   ├── api/                # API Routes & WebSockets
│   └── main.py             # Entry Point
├── frontend/               # UI Assets
│   ├── css/                # Tailwind & Custom Styles
│   ├── js/                 # App Logic
│   └── index.html          # Single Page Application
├── strategies/             # User Strategies (Versioned)
├── data/                   # Data Storage (Parquet/SQLite)
└── requirements.txt        # Dependencies
```

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
