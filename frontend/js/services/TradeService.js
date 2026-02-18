import { api } from '../core/ApiClient.js';

export class TradeService {
    async start(mode, config = {}) {
        return await api.post('/trade/start', { mode, exchange_config: config });
    }

    async stop() {
        return await api.post('/trade/stop', {});
    }

    async getStatus() {
        return await api.get('/trade/status');
    }
}

export const tradeService = new TradeService();
