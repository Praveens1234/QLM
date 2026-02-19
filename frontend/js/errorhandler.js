window.onerror = function (msg, url, line, col, error) {
    const errorHtml = `
   <div style="position:fixed; top:0; left:0; width:100%; height:100%; background:#0f172a; color:#f87171; padding:2rem; z-index:9999; font-family:monospace; overflow:auto;">
      <h1 style="font-size:1.5rem; font-weight:bold; margin-bottom:1rem; color:#ef4444;">Application Critical Error</h1>
      <div style="background:#1e293b; padding:1.5rem; border-radius:0.5rem; border:1px solid #334155; margin-bottom:1rem;">
          <p style="margin-bottom:0.5rem; font-weight:bold; font-size:1.1rem;">${msg}</p>
          <p style="color:#94a3b8; font-size:0.875rem; margin-bottom:1rem;">${url}:${line}:${col}</p>
          <pre style="white-space:pre-wrap; color:#cbd5e1; font-size:0.875rem; background:#0f172a; padding:1rem; border-radius:0.25rem;">${error?.stack || 'No stack trace available'}</pre>
      </div>
      <button onclick="window.location.reload()" style="padding:0.75rem 1.5rem; background:#4f46e5; color:white; border:none; border-radius:0.375rem; cursor:pointer; font-weight:bold;">Reload Application</button>
   </div>`;
    document.body.innerHTML += errorHtml;
};

window.addEventListener('unhandledrejection', event => {
    console.error("Unhandled Rejection:", event.reason);
});
