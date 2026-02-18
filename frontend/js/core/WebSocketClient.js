export class WebSocketClient {
    constructor() {
        this.url = `ws://${window.location.host}/api/ws`;
        this.socket = null;
        this.listeners = [];
        this.reconnectInterval = 2000;
    }

    connect() {
        if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) return;

        this.socket = new WebSocket(this.url);

        this.socket.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                this.notify(msg);
            } catch (e) {
                console.error("WS Parse Error", e);
            }
        };

        this.socket.onopen = () => console.log("WS Connected");

        this.socket.onclose = (e) => {
            console.log("WS Disconnected. Reconnecting...", e.reason);
            setTimeout(() => this.connect(), this.reconnectInterval);
        };

        this.socket.onerror = (err) => {
            console.error("WS Error", err);
            this.socket.close();
        };
    }

    subscribe(callback) {
        this.listeners.push(callback);
        return () => {
            this.listeners = this.listeners.filter(l => l !== callback);
        };
    }

    notify(msg) {
        this.listeners.forEach(listener => listener(msg));
    }
}

export const wsClient = new WebSocketClient();
