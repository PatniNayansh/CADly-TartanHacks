// Cadly v2 — AI Design Review Board UI

async function runAIReview() {
    const btn = document.getElementById('reviewBtn');
    const placeholder = document.getElementById('reviewPlaceholder');
    const loading = document.getElementById('reviewLoading');
    const results = document.getElementById('reviewResults');

    btn.disabled = true;
    btn.textContent = 'Review in Progress...';
    if (placeholder) placeholder.style.display = 'none';
    if (loading) loading.style.display = 'flex';
    if (results) results.innerHTML = '';

    try {
        const resp = await apiPost('/api/review', {});
        if (!resp.success) {
            showToast(resp.error?.message || 'Failed to start review', 'error');
            if (loading) loading.style.display = 'none';
            if (placeholder) placeholder.style.display = 'block';
        }
        // Results arrive via WebSocket 'ai_review' event
    } catch (err) {
        showToast(`Review failed: ${err.message}`, 'error');
        if (loading) loading.style.display = 'none';
        if (placeholder) placeholder.style.display = 'block';
    } finally {
        btn.disabled = false;
        btn.textContent = 'Run AI Design Review';
    }
}

function renderAIReview(data) {
    const results = document.getElementById('reviewResults');
    const placeholder = document.getElementById('reviewPlaceholder');
    if (!results) return;
    if (placeholder) placeholder.style.display = 'none';

    let html = '';

    // Synthesis (executive summary)
    if (data.has_synthesis && data.synthesis) {
        const s = data.synthesis;
        const scoreColor = (s.manufacturability_score || 0) >= 7 ? 'var(--success)' :
                           (s.manufacturability_score || 0) >= 4 ? 'var(--warning)' : 'var(--critical)';
        html += `
            <div class="review-synthesis">
                <div class="review-synthesis-header">
                    <h2 class="section-title">Board Recommendation</h2>
                    ${s.manufacturability_score ? `<span class="review-score" style="color: ${scoreColor}">${s.manufacturability_score}/10</span>` : ''}
                </div>
                ${s.recommended_process ? `<div class="review-rec-process">Recommended: <strong>${s.recommended_process}</strong> (${s.confidence || 'medium'} confidence)</div>` : ''}
                <div class="review-summary">${s.executive_summary || ''}</div>
                ${renderTopFindings(s.top_findings)}
                ${renderActionItems(s.action_items)}
                ${renderProcessComparison(s.process_comparison)}
            </div>`;
    }

    // Agent cards
    if (data.agents && data.agents.length > 0) {
        html += '<h2 class="section-title" style="margin-top: 16px;">Specialist Assessments</h2>';
        html += data.agents.map(a => renderAgentCard(a)).join('');
    }

    results.innerHTML = html;

    // Dedalus badge
    const badge = document.getElementById('reviewDedalusBadge');
    if (badge) {
        badge.innerHTML = `
            <div class="dedalus-badge">
                <span class="dedalus-icon">&#9889;</span>
                Powered by Dedalus Labs AI Agent Swarm
            </div>`;
    }
}

function renderAgentCard(agent) {
    const hasError = agent.error;
    return `
        <div class="review-agent-card ${hasError ? 'agent-error' : ''}">
            <div class="review-agent-header" onclick="this.parentElement.classList.toggle('open')">
                <span class="review-agent-icon">${agent.icon || '&#129302;'}</span>
                <span class="review-agent-name">${agent.name}</span>
                ${agent.score ? `<span class="review-agent-score">${agent.score}/10</span>` : ''}
                <span class="review-agent-toggle">&#9660;</span>
            </div>
            <div class="review-agent-body">
                <div class="review-agent-assessment">${agent.assessment}</div>
                ${agent.concerns && agent.concerns.length ? `
                    <div class="review-agent-section">
                        <strong>Concerns:</strong>
                        <ul>${agent.concerns.map(c => `<li>${c}</li>`).join('')}</ul>
                    </div>` : ''}
                ${agent.recommendations && agent.recommendations.length ? `
                    <div class="review-agent-section">
                        <strong>Recommendations:</strong>
                        <ul>${agent.recommendations.map(r => `<li>${r}</li>`).join('')}</ul>
                    </div>` : ''}
            </div>
        </div>`;
}

function renderTopFindings(findings) {
    if (!findings || !findings.length) return '';
    return `
        <div class="review-findings">
            <strong>Top Findings:</strong>
            ${findings.map(f => {
                const sev = f.severity || 'info';
                return `<div class="review-finding ${sev}">
                    <span class="finding-severity">${sev}</span>
                    <span class="finding-text">${f.finding}</span>
                    <span class="finding-source">${f.source_agent || ''}</span>
                </div>`;
            }).join('')}
        </div>`;
}

function renderActionItems(items) {
    if (!items || !items.length) return '';
    return `
        <div class="review-actions">
            <strong>Action Items:</strong>
            ${items.map(item => `
                <div class="review-action-item">
                    <span class="action-priority">#${item.priority}</span>
                    <div class="action-content">
                        <div class="action-text">${item.action}</div>
                        <div class="action-reason">${item.reason || ''}</div>
                    </div>
                </div>
            `).join('')}
        </div>`;
}

function renderProcessComparison(comparison) {
    if (!comparison) return '';
    const processes = [
        { name: 'FDM', score: comparison.fdm_score },
        { name: 'SLA', score: comparison.sla_score },
        { name: 'CNC', score: comparison.cnc_score },
    ].filter(p => p.score);

    if (!processes.length) return '';

    return `
        <div class="review-process-comparison">
            <strong>Process Scores:</strong>
            <div class="review-process-bars">
                ${processes.map(p => {
                    const pct = (p.score / 10) * 100;
                    const color = p.score >= 7 ? 'var(--success)' :
                                  p.score >= 4 ? 'var(--warning)' : 'var(--critical)';
                    return `
                        <div class="review-process-bar-row">
                            <span class="bar-label">${p.name}</span>
                            <div class="bar-track">
                                <div class="bar-fill" style="width: ${pct}%; background: ${color}"></div>
                            </div>
                            <span class="bar-value">${p.score}/10</span>
                        </div>`;
                }).join('')}
            </div>
            ${comparison.best_for_prototype ? `<div class="review-best-for">Prototype: <strong>${comparison.best_for_prototype}</strong> | Production: <strong>${comparison.best_for_production || 'N/A'}</strong></div>` : ''}
        </div>`;
}
