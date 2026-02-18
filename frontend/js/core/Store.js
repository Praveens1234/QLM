export class Store {
    constructor() {
        this.state = {
            datasets: [],
            strategies: [],
            sessions: [],
            user: null,
            config: {},
            mcpStatus: { active: false, logs: [] }
        };
        this.listeners = [];
    }

    subscribe(listener) {
        this.listeners.push(listener);
        return () => {
            this.listeners = this.listeners.filter(l => l !== listener);
        };
    }

    setState(newState) {
        this.state = { ...this.state, ...newState };
        this.notify();
    }

    getState() {
        return this.state;
    }

    notify() {
        this.listeners.forEach(listener => listener(this.state));
    }

    /**
     * Connect a component function to the store.
     * @param {Function} component - Function that renders based on state.
     * @param {Function} selector - Optional function to select specific state.
     */
    connect(component, selector = s => s) {
        return () => {
            const state = selector(this.getState());
            component(state);
            this.subscribe((newState) => {
                component(selector(newState));
            });
        };
    }
}

export const store = new Store();
