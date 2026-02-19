import { api } from '../core/ApiClient.js';
import { wsClient } from '../core/WebSocketClient.js';

export class BacktestService {
    constructor() {
        this.progressListeners = [];
        this.resultListeners = [];
        this.errorListeners = [];

        wsClient.subscribe((msg) => {
            if (msg.type === 'progress') {
                this.notifyProgress(msg);
            } else if (msg.type === 'finished') {
                this.notifyResult(msg.results);
            } else if (msg.type === 'error') {
                this.notifyError(msg);
            }
        });
    }

    onProgress(cb) { this.progressListeners.push(cb); }
    onResult(cb) { this.resultListeners.push(cb); }
    onError(cb) { this.errorListeners.push(cb); }

    notifyProgress(msg) { this.progressListeners.forEach(cb => cb(msg)); }
    notifyResult(res) { this.resultListeners.forEach(cb => cb(res)); }
    notifyError(err) { this.errorListeners.forEach(cb => cb(err)); }

    async runBacktest(datasetId, strategyName) {
        return await api.post('/backtest/run', { dataset_id: datasetId, strategy_name: strategyName });
    }

    async runOptimization(config) {
        // config: { dataset_id, strategy_name, method, target_metric, params? }
        return await api.post('/backtest/optimize', config);
    }
}

export const backtestService = new BacktestService();
