export class CodeEditor {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.editor = null;
        this.init();
    }

    init() {
        if (!this.container) return;

        require.config({ paths: { 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs' } });
        require(['vs/editor/editor.main'], () => {
            this.editor = monaco.editor.create(this.container, {
                value: "# Select a strategy or create one",
                language: 'python',
                theme: 'vs-dark',
                automaticLayout: true,
                minimap: { enabled: false },
                padding: { top: 16, bottom: 16 },
                fontSize: 13,
                fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                scrollBeyondLastLine: false,
                renderLineHighlight: 'all',
            });
        });
    }

    setValue(code) {
        if (this.editor) {
            this.editor.setValue(code);
        } else {
            // Fallback if editor not ready (rare race condition)
            setTimeout(() => this.setValue(code), 100);
        }
    }

    getValue() {
        return this.editor ? this.editor.getValue() : "";
    }

    layout() {
        if (this.editor) this.editor.layout();
    }
}
