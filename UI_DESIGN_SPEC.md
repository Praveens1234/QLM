# UI/UX Design Specification: QLM 2.0 (Terminal Edition)

## 1. Design Philosophy
*   **Aesthetic**: "Dark Mode Financial Terminal" (Bloomberg/Refinitiv style).
*   **Palette**:
    *   **Background**: Deep Slate (`#020617` to `#0f172a`).
    *   **Accents**: Indigo (Primary), Emerald (Profit/Success), Rose (Loss/Error), Amber (Warning/Pending).
    *   **Text**: High contrast Slate (`#f8fafc` for headers, `#94a3b8` for metadata).
*   **Typography**: `Inter` for UI elements, `JetBrains Mono` for all data, code, and financial figures.

## 2. Key UX Improvements

### 2.1 Visualization (The "Missing Link")
Current state: Backtest results are text/tables.
**Target State**:
*   **Interactive Charts**: Use `lightweight-charts` (Canvas-based, high performance).
*   **Dual-Pane View**:
    *   **Top Pane**: Candlestick Chart (OHLCV) with overlay markers for Trade Entry (Triangle Up/Down) and Exit.
    *   **Bottom Pane**: Equity Curve (Area Chart) showing portfolio growth/drawdown over time.
*   **Responsiveness**: Charts must resize dynamically when the sidebar toggles or window resizes.

### 2.2 Non-Blocking Feedback
Current state: `alert("Saved")` (Blocking).
**Target State**:
*   **Toast Notifications**: A stack of notifications in the bottom-right corner.
*   **Types**: Success (Green), Error (Red), Info (Blue).
*   **Animation**: Slide-in/Fade-out.

### 2.3 Layout Refinements
*   **Strategy Lab**: Maximize code editor vertical space.
*   **Dashboard**: Add a "Market Pulse" chart (mock or real data snippet) to make it alive.
*   **Backtest Runner**: Move Configuration to a sidebar/top bar to give maximum real estate to the Results Chart.

## 3. Technical Architecture

### Frontend Libraries
*   **Tailwind CSS** (Styling).
*   **Lightweight Charts** (TradingView) - via CDN.
*   **Monaco Editor** (Code) - Existing.
*   **FontAwesome** (Icons) - Existing.

### Data Structures (Backend Requirements)
To support the charts, the `run_backtest` API must return:
1.  **`ohlcv`**: `[{ time: 16788..., open: 100, high: 105, low: 99, close: 102 }, ...]`
2.  **`equity_curve`**: `[{ time: 16788..., value: 10050 }, ...]`
3.  **`trades`**: Augmented with specific entry/exit timestamps matching the chart time scale.

## 4. Mobile Responsiveness
*   **Sidebar**: Hamburger menu (already implemented, refine animations).
*   **Charts**: Disable scrolling on charts to prevent page scroll locking? Or handle touch events gracefully.
*   **Tables**: Horizontal scroll overflow for data tables.

## 5. Implementation Roadmap
1.  **Backend**: Upgrade `BacktestEngine` to record equity history and snapshot OHLCV.
2.  **Frontend**:
    *   Import `lightweight-charts`.
    *   Build `Toast` component.
    *   Build `Chart` component.
    *   Update `app.js` to render these on backtest completion.
