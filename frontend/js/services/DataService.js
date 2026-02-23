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

    async getDiscrepancies(id) {
        return await api.get(`/data/${id}/discrepancies`);
    }

    async getWindow(id, index) {
        return await api.get(`/data/${id}/window/${index}`);
    }

    async updateRow(id, index, rowData) {
        return await api.put(`/data/${id}/row/${index}`, rowData);
    }

    async deleteRow(id, index) {
        return await api.delete(`/data/${id}/row/${index}`);
    }

    async interpolateGap(id, index) {
        return await api.post(`/data/${id}/interpolate/${index}`);
    }

    async autofixRow(id, index) {
        return await api.post(`/data/${id}/autofix/${index}`);
    }

    async inspectRow(id, query) {
        return await api.get(`/data/${id}/inspect?query=${encodeURIComponent(query)}`);
    }
}

export const dataService = new DataService();
