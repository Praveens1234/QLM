export class ApiClient {
    constructor(baseUrl = '/api') {
        this.baseUrl = baseUrl;
    }

    async get(endpoint) {
        return this.request(endpoint, { method: 'GET' });
    }

    async post(endpoint, body) {
        return this.request(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
    }

    async delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    }

    async upload(endpoint, formData) {
        return this.request(endpoint, {
            method: 'POST',
            body: formData
            // Content-Type is set automatically by browser for FormData
        });
    }

    async request(endpoint, options = {}) {
        try {
            const res = await fetch(`${this.baseUrl}${endpoint}`, options);
            const contentType = res.headers.get("content-type");

            let data;
            if (contentType && contentType.includes("application/json")) {
                data = await res.json();
            } else {
                data = await res.text();
            }

            if (!res.ok) {
                let errorMsg = (data && data.detail) || (data && data.error) || res.statusText;
                if (typeof errorMsg === 'object') errorMsg = JSON.stringify(errorMsg);
                throw new Error(errorMsg);
            }
            return data;
        } catch (error) {
            console.error(`API Error [${endpoint}]:`, error);
            if (window.Toast) window.Toast.error(error.message);
            throw error;
        }
    }
}

export const api = new ApiClient();
