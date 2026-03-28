import { api } from '../core/ApiClient.js';

export class ChartService {
    /**
     * Get chart metadata including valid timeframes
     * @param {string} datasetId 
     * @returns {Promise<Object>}
     */
    async getMeta(datasetId) {
        return await api.get(`/chart/${datasetId}/meta`);
    }

    /**
     * Get resampled OHLCV bars
     * @param {string} datasetId 
     * @param {number} tfSeconds 
     * @param {number|null} endCursor 
     * @param {number} limit 
     * @returns {Promise<Object>}
     */
    async getBars(datasetId, tfSeconds, endCursor = null, limit = 2000) {
        let url = `/chart/${datasetId}/bars?tf=${tfSeconds}&limit=${limit}`;
        if (endCursor) {
            url += `&end=${endCursor}`;
        }
        return await api.get(url);
    }
}

export const chartService = new ChartService();
