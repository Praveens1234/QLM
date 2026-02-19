import { Router } from './core/Router.js';
import { store } from './core/Store.js';
import { api } from './core/ApiClient.js';
import { wsClient } from './core/WebSocketClient.js';
import { Layout } from './components/Layout.js';
import { DashboardView } from './views/DashboardView.js';
import { DataView } from './views/DataView.js';
import { StrategyView } from './views/StrategyView.js';
import { BacktestView } from './views/BacktestView.js';
import { AssistantView } from './views/AssistantView.js';
import { MCPView } from './views/MCPView.js';
import { SettingsView } from './views/SettingsView.js';
import { toast } from './notifications.js';

const dashboardView = new DashboardView();
const dataView = new DataView();
const strategyView = new StrategyView();
const backtestView = new BacktestView();
const assistantView = new AssistantView();
const mcpView = new MCPView();
const settingsView = new SettingsView();

// Initialize Routes
const routes = {
    'dashboard': { action: () => dashboardView.mount() },
    'data': { action: () => dataView.mount() },
    'strategies': { action: () => strategyView.mount() },
    'backtest': { action: () => backtestView.mount() },
    'assistant': { action: () => assistantView.mount() },
    'mcp': { action: () => mcpView.mount() },
    'settings': { action: () => settingsView.mount() }
};

// Global App State
const app = {
    router: new Router(routes),
    layout: new Layout(),
    store,
    api
};

// Expose legacy functions to window for onclick handlers (temporary bridge)
window.router = app.router;
window.api = api;

// Connect WebSocket for real-time updates (backtest progress, events)
wsClient.connect();

// Init
window.onload = () => {
    // Initial Route
    app.router.handleHashChange();
};
