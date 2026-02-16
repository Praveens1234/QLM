// Toast Notification System
const Toast = {
    container: null,

    init: () => {
        if (!document.getElementById('toast-container')) {
            const container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm pointer-events-none';
            document.body.appendChild(container);
            Toast.container = container;
        } else {
            Toast.container = document.getElementById('toast-container');
        }
    },

    show: (message, type = 'info', duration = 5000) => {
        if (!Toast.container) Toast.init();

        const toast = document.createElement('div');
        toast.className = `
            pointer-events-auto flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg border border-slate-700
            transform transition-all duration-300 translate-y-2 opacity-0
            ${type === 'error' ? 'bg-rose-950 text-rose-200' :
              type === 'success' ? 'bg-emerald-950 text-emerald-200' :
              'bg-slate-800 text-slate-200'}
        `;

        const icon = type === 'error' ? 'fa-circle-exclamation' :
                     type === 'success' ? 'fa-circle-check' : 'fa-info-circle';

        toast.innerHTML = `
            <i class="fa-solid ${icon} text-lg"></i>
            <div class="text-xs font-medium">${message}</div>
        `;

        Toast.container.appendChild(toast);

        // Animate In
        requestAnimationFrame(() => {
            toast.classList.remove('translate-y-2', 'opacity-0');
        });

        // Remove after duration
        setTimeout(() => {
            toast.classList.add('translate-y-2', 'opacity-0');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    },

    error: (msg) => Toast.show(msg, 'error'),
    success: (msg) => Toast.show(msg, 'success'),
    info: (msg) => Toast.show(msg, 'info')
};

// Global Error Handler
window.addEventListener('unhandledrejection', event => {
    console.error('Unhandled promise rejection:', event.reason);
    Toast.error(`System Error: ${event.reason.message || event.reason}`);
});
