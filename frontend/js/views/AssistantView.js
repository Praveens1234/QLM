import { aiService } from '../services/AIService.js';
import { Router } from '../core/Router.js'; // For navigating to strategies

export class AssistantView {
    constructor() {
        this.container = document.getElementById('page-assistant');
        this.currentSessionId = null;
        this.bindEvents();
    }

    bindEvents() {
        const btnNew = document.querySelector('#page-assistant button i.fa-plus')?.parentElement;
        if(btnNew) btnNew.addEventListener('click', () => this.newSession());

        const input = document.getElementById('ai-input');
        const sendBtn = document.getElementById('ai-send-btn');

        if(sendBtn) sendBtn.addEventListener('click', () => this.sendMessage());
        if(input) input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendMessage();
        });

        // Code Block Apply Delegation
        const chatContainer = document.getElementById('chat-container');
        if (chatContainer) {
            chatContainer.addEventListener('click', (e) => {
                const btn = e.target.closest('button[data-code]');
                if (btn) {
                    this.applyCode(btn.dataset.code);
                }
            });
        }
    }

    async mount() {
        await this.loadSessions();
        // If we have sessions and no current one, load the first
        if (!this.currentSessionId) {
            const list = document.getElementById('session-list');
            const firstId = list.firstChild?.dataset?.id;
            if (firstId) this.loadSession(firstId);
        }
    }

    async loadSessions() {
        try {
            const sessions = await aiService.listSessions();
            this.renderSessionList(sessions);
        } catch (e) {}
    }

    renderSessionList(sessions) {
        const list = document.getElementById('session-list');
        if (!list) return;

        list.innerHTML = sessions.map(s => `
            <li class="flex items-center justify-between p-2 rounded-lg cursor-pointer transition-colors text-sm session-item ${s.id === this.currentSessionId ? 'bg-indigo-600/10 text-indigo-400 font-medium' : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'}" data-id="${s.id}">
                <span class="truncate pr-2">${s.title}</span>
                <button aria-label="Delete Session" class="btn-delete text-slate-600 hover:text-rose-500 p-1 rounded opacity-60 hover:opacity-100" data-id="${s.id}">
                    <i class="fa-solid fa-times text-xs"></i>
                </button>
            </li>
        `).join('');

        // Bind events
        list.querySelectorAll('.session-item').forEach(el => {
            el.addEventListener('click', () => this.loadSession(el.dataset.id));
        });

        list.querySelectorAll('.btn-delete').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.deleteSession(btn.dataset.id);
            });
        });
    }

    async newSession() {
        const title = prompt("Session Title:", "New Analysis");
        if (!title) return;

        try {
            const session = await aiService.createSession(title);
            this.currentSessionId = session.id;
            await this.loadSessions();
            this.loadSession(session.id);
        } catch (e) {}
    }

    async deleteSession(id) {
        if (!confirm("Delete this chat?")) return;
        try {
            await aiService.deleteSession(id);
            if (this.currentSessionId === id) {
                this.currentSessionId = null;
                document.getElementById('chat-container').innerHTML = '';
            }
            await this.loadSessions();
        } catch (e) {}
    }

    async loadSession(id) {
        this.currentSessionId = id;
        this.loadSessions(); // Re-render list to update active state

        const container = document.getElementById('chat-container');
        container.innerHTML = '<div class="text-center p-4 text-xs text-slate-500 animate-pulse">Loading History...</div>';

        try {
            const history = await aiService.getHistory(id);
            container.innerHTML = '';

            if (history.length === 0) {
                this.appendMessage('system', "Started new session. How can I help?");
            }

            history.forEach(msg => {
                if (msg.role === 'user') this.appendMessage('user', msg.content);
                if (msg.role === 'assistant') this.appendMessage('ai', msg.content);
            });
        } catch (e) {
            container.innerHTML = '<div class="text-center p-4 text-xs text-rose-500">Error loading history.</div>';
        }
    }

    async sendMessage() {
        const input = document.getElementById('ai-input');
        const message = input.value.trim();
        if (!message) return;

        if (!this.currentSessionId) {
            if(window.Toast) window.Toast.error("Please create a session first.");
            return;
        }

        input.value = '';
        this.appendMessage('user', message);

        const loadingId = this.appendMessage('ai', '<span class="animate-pulse">Thinking...</span>');

        try {
            const data = await aiService.sendMessage(message, this.currentSessionId);

            const loadingEl = document.getElementById(loadingId);
            if(loadingEl) loadingEl.remove();

            this.appendMessage('ai', data.response);
        } catch (e) {
            const loadingEl = document.getElementById(loadingId);
            if(loadingEl) loadingEl.innerHTML = `<span class="text-rose-400">Error: ${e.message}</span>`;
        }
    }

    appendMessage(role, text) {
        const container = document.getElementById('chat-container');
        const div = document.createElement('div');
        const id = 'msg-' + Date.now();
        div.id = id;

        div.className = "flex w-full mb-4 " + (role === 'user' ? "justify-end" : "justify-start");

        const bubbleClass = role === 'user'
            ? "bg-indigo-600 text-white rounded-2xl rounded-tr-none"
            : (role === 'system' ? "bg-slate-800/50 text-slate-400 text-xs italic text-center w-full bg-transparent" : "bg-slate-800 text-slate-200 rounded-2xl rounded-tl-none border border-slate-700");

        const innerDiv = document.createElement('div');
        innerDiv.className = `max-w-[85%] p-4 shadow-sm ${bubbleClass} text-sm leading-relaxed`;

        // Markdown formatting logic (simplified)
        let html = text
            .replace(/</g, "&lt;").replace(/>/g, "&gt;")
            .replace(/```python([\s\S]*?)```/g, (match, code) => {
                return `<div class="mt-2 mb-2 bg-slate-950 rounded-lg border border-slate-900 overflow-hidden group relative">
                    <div class="bg-slate-900 px-3 py-1 text-[10px] text-slate-500 font-mono uppercase border-b border-slate-800 flex justify-between items-center">
                        <span>Python</span>
                        <button aria-label="Apply Code" data-code="${encodeURIComponent(code)}" class="text-indigo-400 hover:text-indigo-300 opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1">
                            <i class="fa-solid fa-arrow-right-to-bracket"></i> Apply
                        </button>
                    </div>
                    <pre class="p-3 overflow-x-auto text-xs"><code class="language-python">${code}</code></pre>
                </div>`;
            })
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');

        innerDiv.innerHTML = html;
        div.appendChild(innerDiv);

        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
        return id;
    }

    applyCode(encodedCode) {
        const code = decodeURIComponent(encodedCode);
        if (window.editor) {
            window.editor.setValue(code);
            // Navigate to Strategy Lab
            window.location.hash = 'strategies';
            if(window.Toast) window.Toast.success("Code applied to editor!");
        }
    }
}
