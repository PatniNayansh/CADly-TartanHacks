// Violation list rendering and fix actions

function renderSummary(data) {
    const section = document.getElementById('summary');
    section.style.display = 'block';
    document.getElementById('emptyState').style.display = 'none';

    // Recalculate counts from the (possibly filtered) violations list
    const violations = data.violations || [];
    const criticalCount = violations.filter(v => v.severity === 'critical').length;
    const warningCount = violations.filter(v => v.severity === 'warning').length;
    const suggestionCount = violations.filter(v => v.severity === 'suggestion').length;

    document.getElementById('partName').textContent = data.part_name || 'Unknown Part';
    document.getElementById('totalViolations').textContent = violations.length;
    document.getElementById('criticalCount').textContent = criticalCount;
    document.getElementById('warningCount').textContent = warningCount;

    const badge = document.getElementById('processRecommendation');
    const proc = (data.recommended_process || 'FDM').toUpperCase();
    badge.textContent = `Best: ${proc}`;
    badge.className = `badge badge-${(data.recommended_process || 'fdm').toLowerCase()}`;

    const card = document.getElementById('summaryCard');
    if (criticalCount > 0) {
        card.style.borderTop = '3px solid var(--critical)';
    } else if (warningCount > 0) {
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
            </div>`;
        if (fixAllBtn) fixAllBtn.style.display = 'none';
        return;
    }

    const hasFixable = violations.some(v => v.fixable);
    if (fixAllBtn) fixAllBtn.style.display = hasFixable ? 'inline-block' : 'none';

    // Sort: critical first
    const order = { critical: 0, warning: 1, suggestion: 2 };
    violations.sort((a, b) => (order[a.severity] || 3) - (order[b.severity] || 3));

    violations.forEach(v => {
        const card = document.createElement('div');
        card.className = `violation-card ${v.severity}`;
        const fixDesc = getFixDescription(v);
        const locStr = formatLocation(v.location);
        card.innerHTML = `
            <div class="violation-header">
                <span class="violation-id">${v.rule_id}</span>
                <span class="severity-badge severity-${v.severity}">${v.severity}</span>
            </div>
            <div class="violation-message">${v.message}</div>
            ${locStr ? `<div class="violation-location">${locStr}</div>` : ''}
            <div class="violation-values">
                <span>Current: <strong>${formatValue(v.current_value, v.rule_id)}</strong></span>
                <span>Required: <strong>${formatValue(v.required_value, v.rule_id)}</strong></span>
            </div>
            ${v.fixable ? `
                <div class="fix-action">
                    <span class="fix-description">${fixDesc}</span>
                    <button class="btn-fix" onclick="applyFix('${v.rule_id}', '${v.feature_id}', ${v.required_value}, ${v.current_value})">Auto-Fix</button>
                </div>
            ` : ''}
        `;
        list.appendChild(card);
    });
}

function formatValue(val, ruleId) {
    if (ruleId === 'CNC-003') return `${val.toFixed(1)}:1`;
    if (ruleId === 'FDM-002') return `${val.toFixed(0)}deg`;
    return `${val.toFixed(2)}mm`;
}

function getFixDescription(v) {
    const rid = v.rule_id;
    if (rid === 'FDM-003' || rid === 'GEN-001') {
        return `Will resize hole from ${v.current_value.toFixed(1)}mm to ${v.required_value.toFixed(1)}mm diameter`;
    }
    if (rid === 'FDM-001' || rid === 'SLA-001') {
        return `Will thicken wall from ${v.current_value.toFixed(1)}mm to ${v.required_value.toFixed(1)}mm`;
    }
    if (rid === 'CNC-001') {
        const edgeNum = v.feature_id.replace('edge_', '#');
        return `Will add fillet to edge ${edgeNum} (radius auto-capped for safety)`;
    }
    return 'Will attempt automatic geometry fix';
}

function formatLocation(loc) {
    if (!loc || !Array.isArray(loc) || loc.length < 3) return '';
    const [x, y, z] = loc.map(v => (v * 10).toFixed(1));  // cm to mm
    return `Location: (${x}, ${y}, ${z}) mm`;
}

function renderCost(data) {
    const section = document.getElementById('costSection');
    const table = document.getElementById('costTable');
    section.style.display = 'block';

    table.innerHTML = `
        <div class="cost-row header">
            <span class="cost-cell">Process</span>
            <span class="cost-cell">Material</span>
            <span class="cost-cell">Time</span>
            <span class="cost-cell">Setup</span>
            <span class="cost-cell">Total</span>
        </div>`;

    const rec = data.recommendation;
    data.estimates.forEach(est => {
        const isRec = est.process === rec;
        const row = document.createElement('div');
        row.className = `cost-row ${isRec ? 'recommended' : ''}`;
        row.innerHTML = `
            <span class="cost-cell">
                ${est.process}${isRec ? '<span class="recommended-label">BEST</span>' : ''}
            </span>
            <span class="cost-cell">$${est.material_cost.toFixed(2)}</span>
            <span class="cost-cell">${est.machine_time_hrs.toFixed(1)}h</span>
            <span class="cost-cell">$${est.setup_cost.toFixed(0)}</span>
            <span class="cost-cell cost-total">$${est.total_cost.toFixed(2)}</span>
        `;
        table.appendChild(row);
    });
}

async function applyFix(ruleId, featureId, targetValue, currentValue) {
    const btn = event.target;
    const originalText = btn.textContent;
    btn.textContent = 'Fixing...';
    btn.className = 'btn-fix fixing';
    btn.disabled = true;

    try {
        const data = await apiPost('/api/fix', {
            rule_id: ruleId,
            feature_id: featureId,
            target_value: targetValue,
            current_value: currentValue,
        });

        if (data.success) {
            btn.textContent = 'Fixed!';
            btn.className = 'btn-fix fixed';
            showToast(data.data?.message || 'Fix applied!', 'success');
            // Fade out the violation card
            const card = btn.closest('.violation-card');
            if (card) {
                card.style.transition = 'opacity 0.5s, transform 0.5s';
                card.style.opacity = '0.4';
                card.style.transform = 'translateX(10px)';
            }
            setTimeout(runAnalysis, 1500);
        } else {
            showToast(data.error?.message || 'Fix failed', 'error');
            btn.textContent = originalText;
            btn.className = 'btn-fix';
            btn.disabled = false;
        }
    } catch (err) {
        showToast(`Fix error: ${err.message}`, 'error');
        btn.textContent = originalText;
        btn.className = 'btn-fix';
        btn.disabled = false;
    }
}

async function fixAll() {
    const btn = document.getElementById('fixAllBtn');
    const originalText = btn.textContent;
    btn.textContent = 'Fixing All...';
    btn.disabled = true;

    try {
        const process = document.getElementById('processFilter').value;
        const data = await apiPost('/api/fix-all', { process });

        if (data.success) {
            showToast(data.data?.message || 'Fixes applied!', 'success');
        } else {
            showToast(data.error?.message || 'Fix-all failed', 'error');
        }
        setTimeout(runAnalysis, 2000);
    } catch (err) {
        showToast(`Fix-all error: ${err.message}`, 'error');
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}
