# 🚀 QuantLogic Framework (QLM)

![QLM Banner](https://img.shields.io/badge/Status-Beta-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.9%2B-yellow?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**QuantLogic Framework (QLM)** is a high-performance, modular algorithmic trading backtesting engine built for quantitative researchers and traders. It provides a seamless workflow from **Data Ingestion** to **Strategy Development**, **Validation**, and **Backtesting**.

---

## ✨ Features

### 📊 Data Management
- **Universal Ingestion**: Supports CSV uploads with automatic parsing.
- **Parquet Storage**: Optimized for speed and compression.
- **Metadata Tracking**: Keeps track of symbols, timeframes, and date ranges.

### 🧠 Strategy Engine
- **Class-Based API**: Define strategies using a clean, object-oriented Python interface.
- **Vectorized Indicators**: Built on `pandas` and `numpy` for lightning-fast calculations.
- **Risk Management**: Integrated SL/TP logic and Position Sizing.
- **New! Runtime Validator**:
    - **Syntax Check**: Ensures your code is valid Python.
    - **Security Sandbox**: Blocks dangerous imports (`os`, `sys`).
    - **Interface Compliance**: Verifies required methods.
    - **Runtime Simulation**: Dry-runs your strategy against dummy data to catch logic errors *before* backtesting.

### ⚡ Backtesting Core
- **Event-Driven Execution**: Simulates realistic market conditions.
- **Detailed Metrics**: Win Rate, Sharpe Ratio, Max Drawdown, Profit Factor.
- **Visual Reports**: Interactive charts and trade logs.

### 🖥️ Modern UI
- **Dashboard**: Real-time system status and quick stats.
- **Strategy Editor**: Built-in Monaco Editor with syntax highlighting.
- **Results Viewer**: Comprehensive analysis tools.

---

## 🛠️ Installation

### Prerequisites
- Python 3.9+
- Git

### Setup
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
    The server will start at `http://localhost:8000`.

---

## 🚀 Usage Guide

### 1. Ingest Data
data is stored locally in the `data/` directory. Use the **Data** tab to upload CSV files.
- **Format**: `Date, Open, High, Low, Close, Volume`
- **Supported Timeframes**: M1, H1, D1, etc.

### 2. Develop a Strategy
Navigate to the **Strategies** tab.
- Click **"+"** to create a new strategy.
- Implement the required methods:
    - `define_variables(df)`: Calculate indicators.
    - `entry_long(df, vars)`: Return boolean Series for long signals.
    - `entry_short(df, vars)`: Return boolean Series for short signals.
    - `risk_model(df, vars)`: Define SL/TP levels.
    - `exit(df, vars, trade)`: Custom exit logic.

### 3. Validate Strategy
Click the **"Validate"** button in the toolbar.
- The system will run a **Runtime Simulation** to ensure your code is bug-free and ready for backtesting.

### 4. Run Backtest
Go to the **Backtest** tab.
- Select your **Dataset** and **Strategy**.
- Click **"Run Backtest"**.
- Analyze the results in the **Performance Report**.

---

## 📂 Project Structure

```
QLM/
├── backend/                # Core Application Logic
│   ├── api/                # FastAPI Endpoints
│   ├── core/               # Engine & Data Managers
│   └── main.py             # Entry Point
├── frontend/               # UI Assets
│   ├── css/                # Styles
│   ├── js/                 # Dashboard Logic
│   └── index.html          # Main Interface
├── strategies/             # User Strategies (Versioned)
├── data/                   # Data Storage (GitIgnored)
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
