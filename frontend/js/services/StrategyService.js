import { api } from '../core/ApiClient.js';

export class StrategyService {
    async list() {
        return await api.get('/strategies/');
    }

    async get(name, version) {
        return await api.get(`/strategies/${name}/${version}`);
    }

    async save(name, code) {
        return await api.post('/strategies/', { name, code });
    }

    async delete(name) {
        return await api.delete(`/strategies/${name}`);
    }

    async validate(code) {
        // Validation endpoint expects {name, code}, name is dummy here
        return await api.post('/strategies/validate', { name: "temp", code });
    }

    async listTemplates() {
        return await api.get('/strategies/templates/list');
    }

    async getTemplate(name) {
        return await api.get(`/strategies/templates/${name}`);
    }
}

export const strategyService = new StrategyService();
