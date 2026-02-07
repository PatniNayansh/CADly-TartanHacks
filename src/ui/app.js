// Cadly DFM Agent - Frontend Logic

const API_BASE = window.location.origin;

// Check Fusion 360 connection on load
document.addEventListener('DOMContentLoaded', () => {
    checkConnection();
    setInterval(checkConnection, 10000);
});

async function checkConnection() {
    const statusEl = document.getElementById('connectionStatus');
    const dot = statusEl.querySelector('.status-dot');
    const text = statusEl.querySelector('.status-text');
    try {
        const resp = await fetch(`${API_BASE}/api/health`);
        const data = await resp.json();
        if (data.fusion_connected) {
            dot.className = 'status-dot connected';
            text.textContent = 'Fusion Connected';
        } else {
            dot.className = 'status-dot disconnected';
            text.textContent = 'Fusion Offline';
        }
    } catch {
        dot.className = 'status-dot disconnected';
        text.textContent = 'Server Offline';
    }
}

async function runAnalysis() {
    const btn = document.getElementById('analyzeBtn');
    const loading = document.getElementById('loading');
    const emptyState = document.getElementById('emptyState');
    const process = document.getElementById('processFilter').value;

    btn.disabled = true;
    loading.style.display = 'flex';
    emptyState.style.display = 'none';

    try {
        // Run analysis and cost estimate in parallel
        const [analysisResp, costResp] = await Promise.all([
            fetch(`${API_BASE}/api/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ process }),
            }),
            fetch(`${API_BASE}/api/cost`),
        ]);

        const analysis = await analysisResp.json();
        const cost = await costResp.json();

        if (analysis.success) {
            renderSummary(analysis.data);
            renderViolations(analysis.data.violations);
        }

        if (cost.success) {
            renderCost(cost.data);
        }
    } catch (err) {
        showToast(`Analysis failed: ${err.message}`, 'error');
    } finally {
        btn.disabled = false;
        loading.style.display = 'none';
    }
}

function renderSummary(data) {
    const section = document.getElementById('summary');
    section.style.display = 'block';

    document.getElementById('partName').textContent = data.part_name || 'Unknown Part';
    document.getElementById('totalViolations').textContent = data.violation_count;
    document.getElementById('criticalCount').textContent = data.critical_count;
    document.getElementById('warningCount').textContent = data.warning_count;

    const badge = document.getElementById('processRecommendation');
    const proc = (data.recommended_process || 'FDM').toUpperCase();
    badge.textContent = `Best: ${proc}`;
    badge.className = `badge badge-${proc.toLowerCase()}`;

    // Color the summary card border based on status
    const card = document.getElementById('summaryCard');
    if (data.critical_count > 0) {
        card.style.borderTop = '3px solid var(--critical)';
    } else if (data.warning_count > 0) {
        card.style.borderTop = '3px solid var(--warning)';
    } else {
        card.style.borderTop = '3px solid var(--success)';
    }
}

function renderViolations(violations) {
    const section = document.getElementById('violationsSection');
    const list = document.getElementById('violationsList');
    const fixAllBtn = document.getElementById('fixAllBtn');
    section.style.display = 'block';
    list.innerHTML = '';

    if (!violations || violations.length === 0) {
        list.innerHTML = `
            <div class="all-clear">
                <div class="all-clear-icon">&#10003;</div>
                <p>No manufacturing issues found!</p>
            </div>
        `;
        if (fixAllBtn) fixAllBtn.style.display = 'none';
        return;
    }

    // Show/hide Fix All button
    const hasFixable = violations.some(v => v.fixable);
    if (fixAllBtn) fixAllBtn.style.display = hasFixable ? 'inline-block' : 'none';

    // Sort: critical first, then warning, then suggestion
    const order = { critical: 0, warning: 1, suggestion: 2 };
    violations.sort((a, b) => (order[a.severity] || 3) - (order[b.severity] || 3));

    violations.forEach((v) => {
        const card = document.createElement('div');
        card.className = `violation-card ${v.severity}`;
        card.innerHTML = `
            <div class="violation-header">
                <span class="violation-id">${v.rule_id}</span>
                <span class="severity-badge severity-${v.severity}">${v.severity}</span>
            </div>
            <div class="violation-message">${v.message}</div>
            <div class="violation-values">
                <span>Current: <strong>${formatValue(v.current_value, v.rule_id)}</strong></span>
                <span>Required: <strong>${formatValue(v.required_value, v.rule_id)}</strong></span>
            </div>
            ${v.fixable ? `<button class="btn-fix" onclick="applyFix('${v.rule_id}', '${v.feature_id}', ${v.required_value}, ${v.current_value})">Auto-Fix</button>` : ''}
        `;
        list.appendChild(card);
    });
}

function formatValue(val, ruleId) {
    if (ruleId.includes('002') && ruleId.startsWith('CNC')) return `${val.toFixed(1)}:1`;
    if (ruleId.includes('002') && ruleId.startsWith('FDM')) return `${val.toFixed(0)}°`;
    return `${val.toFixed(1)}mm`;
}

function renderCost(data) {
    const section = document.getElementById('costSection');
    const table = document.getElementById('costTable');
    section.style.display = 'block';
    table.innerHTML = '';

    // Header row
    table.innerHTML = `
        <div class="cost-row header">
            <span class="cost-cell">Process</span>
            <span class="cost-cell">Material</span>
            <span class="cost-cell">Time</span>
            <span class="cost-cell">Total</span>
        </div>
    `;

    const recommendation = data.recommendation;

    data.estimates.forEach((est) => {
        const isRec = est.process === recommendation;
        const row = document.createElement('div');
        row.className = `cost-row ${isRec ? 'recommended' : ''}`;
        row.innerHTML = `
            <span class="cost-cell">
                ${est.process}
                ${isRec ? '<span class="recommended-label">BEST</span>' : ''}
            </span>
            <span class="cost-cell">$${est.material_cost.toFixed(2)}</span>
            <span class="cost-cell">${est.machine_time_hrs.toFixed(1)}h</span>
            <span class="cost-cell cost-total">$${est.total_cost.toFixed(2)}</span>
        `;
        table.appendChild(row);
    });
}

async function applyFix(ruleId, featureId, targetValue, currentValue) {
    const btn = event.target;
    const originalText = btn.textContent;
    btn.textContent = 'Fixing...';
    btn.disabled = true;

    try {
        const resp = await fetch(`${API_BASE}/api/fix`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                rule_id: ruleId,
                feature_id: featureId,
                target_value: targetValue,
                current_value: currentValue,
            }),
        });
        const data = await resp.json();

        if (data.success) {
            showToast(data.message, 'success');

            // Immediately remove this violation card from the UI
            const card = btn.closest('.violation-card');
            if (card) {
                card.style.transition = 'opacity 0.3s, transform 0.3s';
                card.style.opacity = '0';
                card.style.transform = 'translateX(20px)';
                setTimeout(() => card.remove(), 300);
            }

            // Update summary counts
            updateSummaryAfterFix(ruleId);

            // Re-run analysis after longer delay to pick up any remaining issues
            setTimeout(runAnalysis, 3000);
        } else {
            showToast(data.message || 'Fix failed', 'error');
            btn.textContent = originalText;
            btn.disabled = false;
        }
    } catch (err) {
        showToast(`Fix error: ${err.message}`, 'error');
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

function updateSummaryAfterFix(ruleId) {
    // Decrement violation counts in the summary
    const totalEl = document.getElementById('totalViolations');
    const criticalEl = document.getElementById('criticalCount');
    const warningEl = document.getElementById('warningCount');

    if (totalEl) {
        const current = parseInt(totalEl.textContent) || 0;
        totalEl.textContent = Math.max(0, current - 1);
    }

    // Determine severity from rule_id to update the right counter
    const criticalRules = ['FDM-001', 'SLA-001', 'CNC-001'];
    const warningRules = ['FDM-003', 'CNC-002'];

    if (criticalRules.includes(ruleId) && criticalEl) {
        const current = parseInt(criticalEl.textContent) || 0;
        criticalEl.textContent = Math.max(0, current - 1);
    } else if (warningRules.includes(ruleId) && warningEl) {
        const current = parseInt(warningEl.textContent) || 0;
        warningEl.textContent = Math.max(0, current - 1);
    }

    // Check if no violations left - show all-clear
    const remaining = document.querySelectorAll('.violation-card');
    if (remaining.length <= 1) {
        // The card being removed is still in DOM briefly, so <=1
        setTimeout(() => {
            const list = document.getElementById('violationsList');
            const stillRemaining = document.querySelectorAll('.violation-card');
            if (stillRemaining.length === 0 && list) {
                list.innerHTML = `
                    <div class="all-clear">
                        <div class="all-clear-icon">&#10003;</div>
                        <p>All issues fixed!</p>
                    </div>
                `;
                const fixAllBtn = document.getElementById('fixAllBtn');
                if (fixAllBtn) fixAllBtn.style.display = 'none';
            }
        }, 400);
    }
}

async function fixAll() {
    const btn = document.getElementById('fixAllBtn');
    const originalText = btn.textContent;
    btn.textContent = 'Fixing All...';
    btn.disabled = true;

    try {
        const process = document.getElementById('processFilter').value;
        const resp = await fetch(`${API_BASE}/api/fix-all`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ process }),
        });
        const data = await resp.json();

        if (data.success) {
            showToast(data.message, 'success');

            // Immediately remove all fixable violation cards
            document.querySelectorAll('.violation-card .btn-fix').forEach(fixBtn => {
                const card = fixBtn.closest('.violation-card');
                if (card) {
                    card.style.transition = 'opacity 0.3s, transform 0.3s';
                    card.style.opacity = '0';
                    card.style.transform = 'translateX(20px)';
                    setTimeout(() => card.remove(), 300);
                }
            });
            btn.style.display = 'none';
        } else {
            showToast(data.message || 'Fix-all failed', 'error');
        }

        // Re-analyze after longer delay
        setTimeout(runAnalysis, 3500);
    } catch (err) {
        showToast(`Fix-all error: ${err.message}`, 'error');
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

function showToast(message, type = 'success') {
    // Remove existing toasts
    document.querySelectorAll('.toast').forEach((t) => t.remove());

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => toast.remove(), 4000);
}
