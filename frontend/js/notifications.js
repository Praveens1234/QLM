export class ToastSystem {
    constructor() {
        this.container = document.createElement('div');
        this.container.className = 'fixed top-4 right-4 z-50 flex flex-col gap-2 pointer-events-none';
        document.body.appendChild(this.container);
    }

    show(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `
            pointer-events-auto flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg
            transform transition-all duration-300 translate-x-10 opacity-0
            min-w-[300px] max-w-md border backdrop-blur-md
        `;

        // Colors based on type
        if (type === 'success') {
            toast.className += ' bg-emerald-900/80 border-emerald-500/30 text-emerald-100';
            toast.innerHTML = `<i class="fa-solid fa-check-circle text-emerald-400"></i>`;
        } else if (type === 'error') {
            toast.className += ' bg-rose-900/80 border-rose-500/30 text-rose-100';
            toast.innerHTML = `<i class="fa-solid fa-circle-exclamation text-rose-400"></i>`;
        } else {
            toast.className += ' bg-slate-800/90 border-slate-600/30 text-slate-100';
            toast.innerHTML = `<i class="fa-solid fa-info-circle text-indigo-400"></i>`;
        }

        const text = document.createElement('span');
        text.className = 'text-sm font-medium';
        text.innerText = message;
        toast.appendChild(text);

        this.container.appendChild(toast);

        // Animate In
        requestAnimationFrame(() => {
            toast.classList.remove('translate-x-10', 'opacity-0');
        });

        // Auto Dismiss
        setTimeout(() => {
            toast.classList.add('opacity-0', 'translate-x-10');
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    success(msg) { this.show(msg, 'success'); }
    error(msg) { this.show(msg, 'error'); }
    info(msg) { this.show(msg, 'info'); }
}

export const toast = new ToastSystem();
// Backwards compatibility for now
window.Toast = toast;
