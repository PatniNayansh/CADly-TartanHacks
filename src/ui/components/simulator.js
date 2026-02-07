// Process Switch Simulator UI

const PROCESS_LABELS = {
    fdm: 'FDM',
    sla: 'SLA',
    cnc: 'CNC',
    injection_molding: 'Injection Molding',
};

async function runSimulation() {
    const fromEl = document.getElementById('simFrom');
    const toEl = document.getElementById('simTo');
    const btn = document.getElementById('simBtn');
    const results = document.getElementById('simResults');
    const placeholder = document.getElementById('simPlaceholder');

    const fromProcess = fromEl.value;
    const toProcess = toEl.value;

    if (fromProcess === toProcess) {
        showToast('Select two different processes to compare', 'error');
        return;
    }

    btn.disabled = true;
    btn.textContent = 'Simulating...';
    btn.classList.add('loading');
    results.innerHTML = '';
    if (placeholder) placeholder.style.display = 'none';

    try {
        const resp = await apiPost('/api/simulate', {
            from_process: fromProcess,
            to_process: toProcess,
        });

        if (resp.success) {
            renderSimResults(resp.data);
        } else {
            showToast(resp.error?.message || 'Simulation failed', 'error');
            if (placeholder) placeholder.style.display = 'block';
        }
    } catch (err) {
        showToast(`Simulation failed: ${err.message}`, 'error');
        if (placeholder) placeholder.style.display = 'block';
    } finally {
        btn.disabled = false;
        btn.textContent = 'Simulate Switch';
        btn.classList.remove('loading');
    }
}

function renderSimResults(data) {
    const container = document.getElementById('simResults');
    container.innerHTML = '';

    // 1. Verdict banner
    const comp = data.comparison || {};
    const verdict = comp.verdict || {};
    renderVerdict(container, verdict, data);

    // 2. Summary sentence
    if (data.summary) {
        const summaryEl = document.createElement('div');
        summaryEl.className = 'sim-summary';
        summaryEl.textContent = data.summary;
        container.appendChild(summaryEl);
    }

    // 3. Violation diff
    renderViolationDiff(container, data);

    // 4. Cost comparison
    renderCostComparison(container, data);

    // 5. Process comparison cards
    if (comp.from_process && comp.to_process) {
        renderProcessComparison(container, comp);
    }

    // 6. Redesign roadmap
    if (data.redesign_steps && data.redesign_steps.length > 0) {
        renderRedesignRoadmap(container, data.redesign_steps);
    }
}

function renderVerdict(container, verdict, data) {
    const rec = verdict.recommendation || 'neutral';
    const label = verdict.label || 'Analysis Complete';
    const reasons = verdict.reasons || [];

    const colorClass = rec === 'recommended' ? 'good'
        : rec === 'not_recommended' ? 'critical' : 'warning';
    const icon = rec === 'recommended' ? '\u2705'
        : rec === 'not_recommended' ? '\u274c' : '\u2696';

    const from = PROCESS_LABELS[data.from_process] || data.from_process;
    const to = PROCESS_LABELS[data.to_process] || data.to_process;

    const el = document.createElement('div');
    el.className = `sim-verdict ${colorClass}`;
    el.innerHTML = `
        <div class="sim-verdict-header">
            <span class="sim-verdict-icon">${icon}</span>
            <span class="sim-verdict-label">${label}</span>
        </div>
        <div class="sim-verdict-switch">${from} \u2192 ${to}</div>
        ${reasons.length > 0 ? `<ul class="sim-verdict-reasons">${reasons.map(r => `<li>${r}</li>`).join('')}</ul>` : ''}
    `;
    container.appendChild(el);
}

function renderViolationDiff(container, data) {
    const removed = data.removed_violations || [];
    const added = data.new_violations || [];
    const persistent = data.persistent_violations || [];

    const section = document.createElement('div');
    section.className = 'sim-section';

    const total = removed.length + added.length + persistent.length;
    section.innerHTML = `<h3 class="section-title">Violation Changes</h3>`;

    if (total === 0 && removed.length === 0) {
        section.innerHTML += `<div class="sim-no-changes">No violations in either process.</div>`;
        container.appendChild(section);
        return;
    }

    // Stats row
    const stats = document.createElement('div');
    stats.className = 'sim-diff-stats';
    stats.innerHTML = `
        <div class="sim-diff-stat resolved">
            <span class="sim-diff-count">${removed.length}</span>
            <span class="sim-diff-label">Resolved</span>
        </div>
        <div class="sim-diff-stat introduced">
            <span class="sim-diff-count">${added.length}</span>
            <span class="sim-diff-label">New</span>
        </div>
        <div class="sim-diff-stat persistent">
            <span class="sim-diff-count">${persistent.length}</span>
            <span class="sim-diff-label">Unchanged</span>
        </div>
    `;
    section.appendChild(stats);

    // List removed violations
    if (removed.length > 0) {
        const subHeader = document.createElement('div');
        subHeader.className = 'sim-diff-subheader resolved';
        subHeader.textContent = '\u2705 Resolved (no longer apply)';
        section.appendChild(subHeader);
        removed.forEach(v => section.appendChild(buildViolationMini(v, 'resolved')));
    }

    // List new violations
    if (added.length > 0) {
        const subHeader = document.createElement('div');
        subHeader.className = 'sim-diff-subheader introduced';
        subHeader.textContent = '\u26a0 New violations introduced';
        section.appendChild(subHeader);
        added.forEach(v => section.appendChild(buildViolationMini(v, 'introduced')));
    }

    // List persistent violations
    if (persistent.length > 0) {
        const subHeader = document.createElement('div');
        subHeader.className = 'sim-diff-subheader persistent';
        subHeader.textContent = '\u2194 Unchanged';
        section.appendChild(subHeader);
        persistent.forEach(v => section.appendChild(buildViolationMini(v, 'persistent')));
    }

    container.appendChild(section);
}

function buildViolationMini(v, diffClass) {
    const el = document.createElement('div');
    el.className = `sim-violation-mini ${diffClass} ${v.severity || ''}`;
    el.innerHTML = `
        <span class="sim-v-id">${v.rule_id}</span>
        <span class="sim-v-msg">${v.message}</span>
        <span class="severity-badge severity-${v.severity}">${v.severity}</span>
    `;
    return el;
}

function renderCostComparison(container, data) {
    const before = data.cost_before || {};
    const after = data.cost_after || {};
    const delta = data.cost_delta || 0;

    const section = document.createElement('div');
    section.className = 'sim-section';

    const deltaClass = delta < 0 ? 'savings' : delta > 0 ? 'increase' : 'neutral';
    const deltaSign = delta < 0 ? '-' : delta > 0 ? '+' : '';
    const deltaText = delta === 0 ? 'Same cost' : `${deltaSign}$${Math.abs(delta).toFixed(2)}/unit`;

    section.innerHTML = `
        <h3 class="section-title">Cost Impact</h3>
        <div class="sim-cost-comparison">
            <div class="sim-cost-card">
                <div class="sim-cost-label">${PROCESS_LABELS[data.from_process] || data.from_process}</div>
                <div class="sim-cost-value">$${(before.total_cost || 0).toFixed(2)}</div>
                <div class="sim-cost-breakdown">
                    Material: $${(before.material_cost || 0).toFixed(2)} |
                    Time: ${(before.machine_time_hrs || 0).toFixed(1)}h |
                    Setup: $${(before.setup_cost || 0).toFixed(0)}
                </div>
            </div>
            <div class="sim-cost-arrow">\u2192</div>
            <div class="sim-cost-card">
                <div class="sim-cost-label">${PROCESS_LABELS[data.to_process] || data.to_process}</div>
                <div class="sim-cost-value">$${(after.total_cost || 0).toFixed(2)}</div>
                <div class="sim-cost-breakdown">
                    Material: $${(after.material_cost || 0).toFixed(2)} |
                    Time: ${(after.machine_time_hrs || 0).toFixed(1)}h |
                    Setup: $${(after.setup_cost || 0).toFixed(0)}
                </div>
            </div>
        </div>
        <div class="sim-cost-delta ${deltaClass}">${deltaText}</div>
    `;
    container.appendChild(section);
}

function renderProcessComparison(container, comp) {
    const from = comp.from_process || {};
    const to = comp.to_process || {};

    const section = document.createElement('div');
    section.className = 'sim-section';
    section.innerHTML = `<h3 class="section-title">Process Comparison</h3>`;

    const grid = document.createElement('div');
    grid.className = 'sim-process-grid';

    grid.innerHTML = `
        <div class="sim-process-col">
            <div class="sim-process-name">${from.short || ''}</div>
            <div class="sim-process-detail">
                <div class="sim-detail-row"><span>Tolerance</span><strong>\u00b1${from.typical_tolerance_mm || 0}mm</strong></div>
                <div class="sim-detail-row"><span>Finish</span><strong>${from.surface_finish || '-'}</strong></div>
                <div class="sim-detail-row"><span>Best for</span><strong>${from.best_for || '-'}</strong></div>
            </div>
            <div class="sim-pros">
                ${(from.strengths || []).slice(0, 3).map(s => `<div class="sim-pro">\u2713 ${s}</div>`).join('')}
            </div>
            <div class="sim-cons">
                ${(from.weaknesses || []).slice(0, 3).map(w => `<div class="sim-con">\u2717 ${w}</div>`).join('')}
            </div>
        </div>
        <div class="sim-vs">VS</div>
        <div class="sim-process-col">
            <div class="sim-process-name">${to.short || ''}</div>
            <div class="sim-process-detail">
                <div class="sim-detail-row"><span>Tolerance</span><strong>\u00b1${to.typical_tolerance_mm || 0}mm</strong></div>
                <div class="sim-detail-row"><span>Finish</span><strong>${to.surface_finish || '-'}</strong></div>
                <div class="sim-detail-row"><span>Best for</span><strong>${to.best_for || '-'}</strong></div>
            </div>
            <div class="sim-pros">
                ${(to.strengths || []).slice(0, 3).map(s => `<div class="sim-pro">\u2713 ${s}</div>`).join('')}
            </div>
            <div class="sim-cons">
                ${(to.weaknesses || []).slice(0, 3).map(w => `<div class="sim-con">\u2717 ${w}</div>`).join('')}
            </div>
        </div>
    `;

    section.appendChild(grid);
    container.appendChild(section);
}

function renderRedesignRoadmap(container, steps) {
    const section = document.createElement('div');
    section.className = 'sim-section';
    section.innerHTML = `<h3 class="section-title">Redesign Roadmap</h3>`;

    const list = document.createElement('div');
    list.className = 'sim-roadmap';

    steps.forEach(step => {
        const effortColor = step.effort === 'low' ? 'var(--success)'
            : step.effort === 'medium' ? 'var(--warning)' : 'var(--critical)';

        const item = document.createElement('div');
        item.className = `sim-roadmap-step ${step.severity || ''}`;
        item.innerHTML = `
            <div class="sim-step-number">${step.step}</div>
            <div class="sim-step-body">
                <div class="sim-step-action">${step.action}</div>
                <div class="sim-step-detail">${step.detail}</div>
                <div class="sim-step-meta">
                    <span class="sim-step-effort" style="color: ${effortColor}">Effort: ${step.effort}</span>
                    ${step.auto_fixable ? '<span class="sim-step-autofix">Auto-fixable</span>' : ''}
                    <span class="sim-step-rule">${step.rule_id}</span>
                </div>
            </div>
        `;
        list.appendChild(item);
    });

    section.appendChild(list);
    container.appendChild(section);
}
