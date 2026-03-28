/**
 * QLM Toast Notification System
 * Premium toast notifications with auto-dismiss progress bar.
 */

const ICONS = {
    success: 'fa-solid fa-circle-check',
    error:   'fa-solid fa-circle-xmark',
    warning: 'fa-solid fa-triangle-exclamation',
    info:    'fa-solid fa-circle-info',
};

const DURATIONS = {
    success: 3000,
    error:   5000,
    warning: 4000,
    info:    3500,
};

class ToastManager {
    constructor() {
        this.container = null;
        this.toasts = [];
        this._ensureContainer();
    }

    _ensureContainer() {
        this.container = document.getElementById('toast-container');
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = 'toast-container';
            this.container.className = 'toast-container';
            document.body.appendChild(this.container);
        }
    }

    _show(type, message, duration) {
        this._ensureContainer();

        const id = 'toast-' + Date.now() + '-' + Math.random().toString(36).slice(2, 6);
        const durationMs = duration || DURATIONS[type] || 3500;

        const toast = document.createElement('div');
        toast.id = id;
        toast.className = `toast toast-${type}`;
        toast.style.setProperty('--toast-duration', durationMs + 'ms');

        toast.innerHTML = `
            <div class="toast-icon">
                <i class="${ICONS[type] || ICONS.info}"></i>
            </div>
            <div class="toast-body">${this._escapeHtml(message)}</div>
            <button class="toast-close" aria-label="Dismiss">
                <i class="fa-solid fa-xmark"></i>
            </button>
            <div class="toast-progress"></div>
        `;

        // Close button
        toast.querySelector('.toast-close').addEventListener('click', () => {
            this._dismiss(id);
        });

        this.container.appendChild(toast);
        this.toasts.push(id);

        // Auto-dismiss
        setTimeout(() => this._dismiss(id), durationMs);

        // Limit to 5 visible toasts
        while (this.toasts.length > 5) {
            this._dismiss(this.toasts[0]);
        }
    }

    _dismiss(id) {
        const toast = document.getElementById(id);
        if (!toast) return;

        toast.classList.add('closing');
        toast.addEventListener('animationend', () => {
            toast.remove();
            this.toasts = this.toasts.filter(t => t !== id);
        });
    }

    _escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    success(msg, duration) { this._show('success', msg, duration); }
    error(msg, duration)   { this._show('error', msg, duration); }
    warning(msg, duration) { this._show('warning', msg, duration); }
    info(msg, duration)    { this._show('info', msg, duration); }
}

// Singleton
export const toast = new ToastManager();

// Expose globally for legacy onclick handlers and views
window.Toast = toast;
