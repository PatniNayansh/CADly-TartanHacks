// API helpers and WebSocket connection

const API_BASE = window.location.origin;
let ws = null;
let wsReconnectTimer = null;

// ---- HTTP helpers ----

async function apiGet(path) {
    const resp = await fetch(`${API_BASE}${path}`);
    return resp.json();
}

async function apiPost(path, body = {}) {
    const resp = await fetch(`${API_BASE}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    return resp.json();
}

// ---- WebSocket ----

function wsConnect() {
    if (ws && ws.readyState === WebSocket.OPEN) return;

    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${proto}//${location.host}/ws`);

    ws.onopen = () => {
        console.log('WebSocket connected');
        if (wsReconnectTimer) {
            clearInterval(wsReconnectTimer);
            wsReconnectTimer = null;
        }
    };

    ws.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);
            handleWsMessage(msg);
        } catch (e) {
            console.warn('WS parse error:', e);
        }
    };

    ws.onclose = () => {
        console.log('WebSocket disconnected');
        if (!wsReconnectTimer) {
            wsReconnectTimer = setInterval(wsConnect, 5000);
        }
    };

    ws.onerror = () => { /* onclose will fire */ };
}

function handleWsMessage(msg) {
    const statusBar = document.getElementById('wsStatus');
    const statusText = document.getElementById('wsStatusText');

    if (msg.type === 'status') {
        statusBar.style.display = 'flex';
        statusText.textContent = msg.step;
        if (msg.progress >= 1.0) {
            setTimeout(() => { statusBar.style.display = 'none'; }, 1500);
        }
    } else if (msg.type === 'analysis') {
        // Auto-update analysis tab when results arrive via WS
        if (msg.data) {
            renderSummary(msg.data);
            renderViolations(msg.data.violations);
        }
    } else if (msg.type === 'ai_sustainability') {
        // AI agent swarm results for sustainability tab
        const loading = document.getElementById('aiSustainabilityLoading');
        if (loading) loading.style.display = 'none';

        if (msg.data && !msg.data.error) {
            renderAISustainability(msg.data);
        } else {
            console.warn('AI sustainability unavailable:', msg.data?.error);
            const section = document.getElementById('aiSustainabilitySection');
            if (section) {
                section.innerHTML = `
                    <div class="ai-unavailable">
                        <span class="ai-unavailable-icon">&#129302;</span>
                        <span>AI sustainability analysis unavailable. Formula-based scores shown above.</span>
                    </div>`;
                section.style.display = 'block';
            }
        }
    }
}

// ---- Toast ----

function showToast(message, type = 'success') {
    document.querySelectorAll('.toast').forEach(t => t.remove());
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}
