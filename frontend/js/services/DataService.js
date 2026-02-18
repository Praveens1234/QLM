import { api } from '../core/ApiClient.js';

export class DataService {
    async list() {
        return await api.get('/data/');
    }

    async upload(file, symbol, timeframe) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('symbol', symbol);
        formData.append('timeframe', timeframe);
        return await api.upload('/data/upload', formData);
    }

    async importUrl(url, symbol, timeframe) {
        return await api.post('/data/url', { url, symbol, timeframe });
    }

    async delete(id) {
        return await api.delete(`/data/${id}`);
    }
}

export const dataService = new DataService();
