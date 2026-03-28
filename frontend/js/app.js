import { Router } from './core/Router.js';
import { store } from './core/Store.js';
import { api } from './core/ApiClient.js';
import { wsClient } from './core/WebSocketClient.js';
import { Layout } from './components/Layout.js';
import { DashboardView } from './views/DashboardView.js';
import { DataView } from './views/DataView.js';
import { StrategyView } from './views/StrategyView.js';
import { BacktestView } from './views/BacktestView.js';
import { MCPView } from './views/MCPView.js';
import { SettingsView } from './views/SettingsView.js';
import { InspectorView } from './views/InspectorView.js';
import { ChartView } from './views/ChartView.js';
import { toast } from './notifications.js';

// --- Singleton View Instances ---
const dashboardView = new DashboardView();
const dataView = new DataView();
const strategyView = new StrategyView();
const backtestView = new BacktestView();
const mcpView = new MCPView();
const settingsView = new SettingsView();
const inspectorView = new InspectorView();
const chartView = new ChartView(); // Singleton — no more leaks

// Previous route tracking for cleanup
let previousRoute = null;

// Initialize Routes
const routes = {
    'dashboard': { action: () => dashboardView.mount() },
    'data':      { action: () => dataView.mount() },
    'inspector': { action: () => inspectorView.mount() },
    'chart':     { action: () => chartView.mount() },
    'strategies':{ action: () => strategyView.mount() },
    'backtest':  { action: () => backtestView.mount() },
    'mcp':       { action: () => mcpView.mount() },
    'settings':  { action: () => {} }
};

// Global App State
const app = {
    router: new Router(routes),
    layout: new Layout(),
    store,
    api
};

// Expose legacy functions to window for onclick handlers
window.router = app.router;
window.api = api;

// Route change cleanup hook
app.router.beforeEach((newRoute) => {
    // If leaving chart, unmount to free memory
    if (previousRoute === 'chart' && newRoute !== 'chart') {
        chartView.unmount();
    }
    previousRoute = newRoute;
    return true; // allow navigation
});

// Connect WebSocket for real-time updates
wsClient.connect();

// Init
window.onload = () => {
    app.router.handleHashChange();
};
