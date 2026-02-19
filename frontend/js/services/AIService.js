import { api } from '../core/ApiClient.js';

export class AIService {
    async listSessions() {
        return await api.get('/ai/sessions');
    }

    async createSession(title) {
        return await api.post('/ai/sessions', { title });
    }

    async getHistory(sessionId) {
        return await api.get(`/ai/sessions/${sessionId}/history`);
    }

    async deleteSession(sessionId) {
        return await api.delete(`/ai/sessions/${sessionId}`);
    }

    async sendMessage(message, sessionId) {
        return await api.post('/ai/chat', { message, session_id: sessionId });
    }

    async getConfig() {
        return await api.get('/ai/config');
    }

    async getProviders() {
        return await api.get('/ai/config/providers');
    }

    async getActiveConfig() {
        return await api.get('/ai/config/active');
    }

    async setActiveConfig(providerId, modelId) {
        return await api.post('/ai/config/active', { provider_id: providerId, model_id: modelId });
    }

    async addProvider(config) {
        return await api.post('/ai/config/providers', config);
    }

    async fetchModels(providerId) {
        return await api.get(`/ai/config/models/${providerId}`);
    }

    async deleteProvider(providerId) {
        return await api.delete(`/ai/config/providers/${providerId}`);
    }
}

export const aiService = new AIService();
