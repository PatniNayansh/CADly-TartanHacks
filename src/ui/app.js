// Cadly v2 — Core frontend logic

// State
let lastAnalysis = null;
let lastCost = null;
let lastSustainability = null;

// ---- Init ----

document.addEventListener('DOMContentLoaded', () => {
    checkConnection();
    setInterval(checkConnection, 10000);
    wsConnect();

    // Re-filter violations when process dropdown changes
    document.getElementById('processFilter').addEventListener('change', () => {
        if (lastAnalysis) {
            const process = document.getElementById('processFilter').value;
            const filtered = filterViolations(lastAnalysis.violations, process);
            renderSummary({ ...lastAnalysis, violations: filtered });
            renderViolations(filtered);
        }
    });
});

// ---- Connection check ----

async function checkConnection() {
    const statusEl = document.getElementById('connectionStatus');
    const dot = statusEl.querySelector('.status-dot');
    const text = statusEl.querySelector('.status-text');

    try {
        const resp = await apiGet('/api/health');
        if (resp.success && resp.data.fusion_connected) {
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

// ---- Tab switching ----

function switchTab(tabId) {
    // Update tab buttons
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelector(`.tab[data-tab="${tabId}"]`).classList.add('active');

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.getElementById(`tab-${tabId}`).classList.add('active');
}

// ---- Analysis ----

async function runAnalysis() {
    const btn = document.getElementById('analyzeBtn');
    const emptyState = document.getElementById('emptyState');
    const process = document.getElementById('processFilter').value;

    btn.disabled = true;
    btn.textContent = 'Analyzing...';
    btn.classList.add('loading');
    emptyState.style.display = 'none';

    try {
        // Always fetch ALL violations, filter client-side
        const [analysis, cost, sustainability] = await Promise.all([
            apiPost('/api/analyze', { process: 'all' }),
            apiGet('/api/cost'),
            apiGet('/api/sustainability'),
        ]);

        if (analysis.success) {
            lastAnalysis = analysis.data;
            const filtered = filterViolations(analysis.data.violations, process);
            renderSummary({ ...analysis.data, violations: filtered });
            renderViolations(filtered);
        } else {
            showToast(analysis.error?.message || 'Analysis failed', 'error');
        }

        if (cost.success) {
            lastCost = cost.data;
            renderCost(cost.data);
            updateCostDashboard(cost.data);
        }

        if (sustainability.success) {
            lastSustainability = sustainability.data;
            renderSustainability(sustainability.data);
        }

        // Decision summary pulls from all three data sources
        renderDecisionSummary(lastAnalysis, lastCost, lastSustainability);
    } catch (err) {
        showToast(`Analysis failed: ${err.message}`, 'error');
        emptyState.style.display = 'block';
    } finally {
        btn.disabled = false;
        btn.textContent = 'Analyze Part';
        btn.classList.remove('loading');
    }
}

// ---- Cost Dashboard (Costs tab) ----

function updateCostDashboard(costData) {
    const dashboard = document.getElementById('costDashboard');
    if (!dashboard) return;
    dashboard.style.display = 'block';
    document.querySelector('#tab-costs .placeholder-tab h3').textContent = 'Cost Comparison Dashboard';
    document.querySelector('#tab-costs .placeholder-tab p').textContent = '';

    updateCostCurves(1);
}

function updateQuantityLabel(val) {
    document.getElementById('quantityLabel').textContent = Number(val).toLocaleString();
    updateCostCurves(Number(val));
}

async function updateCostCurves(quantity) {
    const container = document.getElementById('costCurvesContainer');
    const crossoverList = document.getElementById('crossoverList');
    if (!container) return;

    try {
        const resp = await apiPost('/api/cost/compare', { quantity });
        if (!resp.success) return;

        const data = resp.data;

        // Find cheapest at this quantity
        let cheapestProcess = '';
        let cheapestUnit = Infinity;
        const rows = data.processes.map(proc => {
            const est = proc.estimates.find(e => e.quantity === quantity)
                || proc.estimates[proc.estimates.length - 1];
            const unitCost = est ? (est.total_cost / Math.max(est.quantity, 1)) : 0;
            if (unitCost < cheapestUnit) {
                cheapestUnit = unitCost;
                cheapestProcess = proc.process;
            }
            return { process: proc.process, unitCost, totalCost: est?.total_cost || 0 };
        });

        container.innerHTML = rows.map(r => `
            <div class="cost-curve-row ${r.process === cheapestProcess ? 'cheapest' : ''}">
                <span class="process">${r.process}</span>
                <span class="unit-cost">$${r.unitCost.toFixed(2)}/unit</span>
                <span>$${r.totalCost.toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 0})} total</span>
            </div>
        `).join('');

        // Crossover points
        if (data.crossover_points && data.crossover_points.length > 0) {
            crossoverList.innerHTML = '<strong>Crossover Points:</strong>' +
                data.crossover_points.map(cp =>
                    `<div class="crossover-item">${cp.message}</div>`
                ).join('');
        } else {
            crossoverList.innerHTML = '';
        }
    } catch (e) {
        console.warn('Cost curves update failed:', e);
    }
}

// ---- Process filter ----

const PROCESS_PREFIX_MAP = {
    fdm: ['FDM'],
    sla: ['SLA'],
    cnc: ['CNC'],
    injection_molding: ['IM'],
};

function filterViolations(violations, process) {
    if (!violations) return [];
    if (process === 'all') return violations;

    const prefixes = PROCESS_PREFIX_MAP[process] || [];
    return violations.filter(v => {
        const prefix = v.rule_id.split('-')[0];
        return prefixes.includes(prefix) || prefix === 'GEN';
    });
}
