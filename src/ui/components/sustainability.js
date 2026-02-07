// Cadly v2 — Sustainability tab rendering

function renderSustainability(data) {
    const dashboard = document.getElementById('sustainabilityDashboard');
    const placeholder = document.getElementById('sustainabilityPlaceholder');
    if (!dashboard) return;

    placeholder.style.display = 'none';
    dashboard.style.display = 'block';

    renderGreenScoreHero(data.green_scores, data.greenest_process);
    renderWasteBars(data.waste);
    renderCarbonBars(data.carbon);
    renderGreenRecommendation(data.recommendation, data.greenest_process);
    renderSavingsTips(data.savings_tips);

    // Show AI loading section (AI results arrive via WebSocket)
    const aiSection = document.getElementById('aiSustainabilitySection');
    if (aiSection) {
        aiSection.style.display = 'block';
        const loading = document.getElementById('aiSustainabilityLoading');
        if (loading) loading.style.display = 'flex';
    }
}

function renderGreenScoreHero(scores, greenest) {
    const container = document.getElementById('greenScoreHero');
    if (!container || !scores.length) return;

    const best = scores.find(s => s.process === greenest) || scores[0];
    const scoreColor = best.score >= 70 ? 'var(--success)' :
                       best.score >= 40 ? 'var(--warning)' : 'var(--critical)';

    container.innerHTML = `
        <div class="green-hero-card">
            <div class="green-hero-main">
                <div class="green-hero-score" style="color: ${scoreColor}">
                    ${best.score}
                </div>
                <div class="green-hero-label">
                    <div class="green-hero-grade" style="color: ${scoreColor}">Grade ${best.grade}</div>
                    <div class="green-hero-process">${best.process}</div>
                    <div class="green-hero-tag">Greenest Option</div>
                </div>
            </div>
            <div class="green-scores-row">
                ${scores.map(s => {
                    const color = s.score >= 70 ? 'var(--success)' :
                                  s.score >= 40 ? 'var(--warning)' : 'var(--critical)';
                    return `
                        <div class="green-score-mini ${s.process === greenest ? 'best' : ''}">
                            <span class="mini-score" style="color: ${color}">${s.score}</span>
                            <span class="mini-label">${s.process}</span>
                            <span class="mini-grade">${s.grade}</span>
                        </div>`;
                }).join('')}
            </div>
        </div>`;
}

function renderWasteBars(wasteData) {
    const container = document.getElementById('wasteBars');
    if (!container || !wasteData.length) return;

    const maxWaste = Math.max(...wasteData.map(w => w.waste_percent), 1);

    container.innerHTML = wasteData.map(w => {
        const pct = (w.waste_percent / maxWaste) * 100;
        const barColor = w.waste_percent > 50 ? 'var(--critical)' :
                         w.waste_percent > 20 ? 'var(--warning)' : 'var(--success)';
        return `
            <div class="sustainability-bar-row">
                <span class="bar-label">${w.process}</span>
                <div class="bar-track">
                    <div class="bar-fill" style="width: ${pct}%; background: ${barColor}"></div>
                </div>
                <span class="bar-value">${w.waste_percent.toFixed(1)}%</span>
                <span class="bar-detail">${w.waste_grams.toFixed(1)}g</span>
            </div>`;
    }).join('');
}

function renderCarbonBars(carbonData) {
    const container = document.getElementById('carbonBars');
    if (!container || !carbonData.length) return;

    const maxCarbon = Math.max(...carbonData.map(c => c.carbon_kg), 0.001);

    container.innerHTML = carbonData.map(c => {
        const pct = (c.carbon_kg / maxCarbon) * 100;
        return `
            <div class="sustainability-bar-row">
                <span class="bar-label">${c.process}</span>
                <div class="bar-track">
                    <div class="bar-fill carbon-bar" style="width: ${pct}%"></div>
                </div>
                <span class="bar-value">${c.carbon_kg.toFixed(3)} kg</span>
                <span class="bar-detail">${c.energy_kwh.toFixed(2)} kWh</span>
            </div>`;
    }).join('');
}

function renderGreenRecommendation(recommendation, greenest) {
    const container = document.getElementById('greenRecommendation');
    if (!container) return;

    container.innerHTML = `
        <div class="green-rec-card">
            <div class="green-rec-icon">&#127807;</div>
            <div class="green-rec-text">${recommendation}</div>
        </div>`;
}

function renderSavingsTips(tips) {
    const container = document.getElementById('savingsTips');
    if (!container) return;

    if (!tips || tips.length === 0) {
        container.innerHTML = '';
        return;
    }

    container.innerHTML = `
        <h2 class="section-title" style="margin-top: 16px;">Savings Opportunities</h2>
        ${tips.map(t => `
            <div class="savings-tip-card">
                <div class="tip-header">${t.from} &#8594; ${t.to}</div>
                <div class="tip-detail">
                    Save <strong>${Math.abs(t.waste_saved_grams).toFixed(1)}g</strong> waste
                    + <strong>${Math.abs(t.carbon_saved_kg).toFixed(3)} kg</strong> CO&#8322;
                </div>
            </div>
        `).join('')}`;
}

// ---- AI-Enriched Sustainability Rendering (Dedalus Agent Swarm) ----

function renderAISustainability(data) {
    const loading = document.getElementById('aiSustainabilityLoading');
    if (loading) loading.style.display = 'none';

    renderAIGreenScores(data.process_analyses, data.greenest_process);
    renderAIRecommendation(data.overall_recommendation);
    renderAIRoadmap(data.sustainability_roadmap);
    renderAITradeOffs(data.trade_offs);
    renderAgentReasoning(data.agent_reasoning);
    renderDedalusBadge();
}

function renderAIGreenScores(analyses, greenest) {
    if (!analyses || !analyses.length) return;

    // Upgrade hero card with AI badge
    const hero = document.getElementById('greenScoreHero');
    if (hero) {
        const best = analyses.find(a => a.process === greenest) || analyses[0];
        const scoreColor = best.score >= 70 ? 'var(--success)' :
                           best.score >= 40 ? 'var(--warning)' : 'var(--critical)';

        hero.innerHTML = `
            <div class="green-hero-card ai-enhanced">
                <div class="ai-badge-inline">AI-Scored</div>
                <div class="green-hero-main">
                    <div class="green-hero-score" style="color: ${scoreColor}">
                        ${best.score}
                    </div>
                    <div class="green-hero-label">
                        <div class="green-hero-grade" style="color: ${scoreColor}">Grade ${best.grade}</div>
                        <div class="green-hero-process">${best.process}</div>
                        <div class="green-hero-tag">Greenest Option</div>
                    </div>
                </div>
                <div class="green-scores-row">
                    ${analyses.map(a => {
                        const color = a.score >= 70 ? 'var(--success)' :
                                      a.score >= 40 ? 'var(--warning)' : 'var(--critical)';
                        return `
                            <div class="green-score-mini ${a.process === greenest ? 'best' : ''}">
                                <span class="mini-score" style="color: ${color}">${a.score}</span>
                                <span class="mini-label">${a.process}</span>
                                <span class="mini-grade">${a.grade}</span>
                            </div>`;
                    }).join('')}
                </div>
            </div>`;
    }

    // Render per-process analysis cards
    const container = document.getElementById('aiGreenScores');
    if (!container) return;

    container.innerHTML = `
        <h2 class="section-title">AI Process Analysis</h2>
        ${analyses.map(a => {
            const scoreColor = a.score >= 70 ? 'var(--success)' :
                               a.score >= 40 ? 'var(--warning)' : 'var(--critical)';
            return `
                <div class="ai-process-card ${a.process === greenest ? 'ai-best' : ''}">
                    <div class="ai-process-header">
                        <span class="ai-process-name">${a.process}</span>
                        <span class="ai-process-score" style="color: ${scoreColor}">${a.score} <small>${a.grade}</small></span>
                    </div>
                    <div class="ai-sub-scores">
                        <div class="sub-score">
                            <span class="sub-label">Waste</span>
                            <div class="sub-bar-track"><div class="sub-bar-fill" style="width: ${(a.waste_sub_score / 40) * 100}%; background: var(--warning)"></div></div>
                            <span class="sub-val">${a.waste_sub_score}/40</span>
                        </div>
                        <div class="sub-score">
                            <span class="sub-label">Carbon</span>
                            <div class="sub-bar-track"><div class="sub-bar-fill" style="width: ${(a.carbon_sub_score / 40) * 100}%; background: var(--accent)"></div></div>
                            <span class="sub-val">${a.carbon_sub_score}/40</span>
                        </div>
                        <div class="sub-score">
                            <span class="sub-label">Recycle</span>
                            <div class="sub-bar-track"><div class="sub-bar-fill" style="width: ${(a.recyclability_sub_score / 20) * 100}%; background: var(--success)"></div></div>
                            <span class="sub-val">${a.recyclability_sub_score}/20</span>
                        </div>
                    </div>
                    <div class="ai-justification">${a.justification}</div>
                    ${a.strengths.length ? `
                        <div class="ai-pills">
                            ${a.strengths.map(s => `<span class="ai-strength">${s}</span>`).join('')}
                            ${a.weaknesses.map(w => `<span class="ai-weakness">${w}</span>`).join('')}
                        </div>` : ''}
                    ${a.contextual_comparison ? `<div class="ai-context-comparison">${a.contextual_comparison}</div>` : ''}
                </div>`;
        }).join('')}`;
}

function renderAIRecommendation(recommendation) {
    const container = document.getElementById('aiRecommendation');
    if (!container || !recommendation) return;

    // Replace the formula-based recommendation
    const oldRec = document.getElementById('greenRecommendation');
    if (oldRec) oldRec.innerHTML = '';

    container.innerHTML = `
        <div class="ai-rec-card">
            <div class="ai-rec-header">
                <span class="ai-rec-icon">&#127807;</span>
                <span class="ai-badge-inline">AI Recommendation</span>
            </div>
            <div class="ai-rec-text">${recommendation}</div>
        </div>`;
}

function renderAIRoadmap(roadmap) {
    const container = document.getElementById('aiRoadmap');
    if (!container || !roadmap || !roadmap.length) return;

    container.innerHTML = `
        <h2 class="section-title">Sustainability Roadmap</h2>
        <div class="roadmap-list">
            ${roadmap.map((step, i) => `
                <div class="roadmap-step">
                    <div class="roadmap-number">${i + 1}</div>
                    <div class="roadmap-text">${step}</div>
                </div>
            `).join('')}
        </div>`;
}

function renderAITradeOffs(tradeOffs) {
    const container = document.getElementById('aiTradeOffs');
    if (!container || !tradeOffs || !tradeOffs.length) return;

    container.innerHTML = `
        <h2 class="section-title">Process Trade-Offs</h2>
        ${tradeOffs.map(t => `
            <div class="tradeoff-card">
                <div class="tradeoff-header">
                    <span class="tradeoff-vs">${t.process_a} vs ${t.process_b}</span>
                    <span class="tradeoff-winner">&#9989; ${t.winner}</span>
                </div>
                <div class="tradeoff-summary">${t.summary}</div>
                ${t.environmental_delta ? `<div class="tradeoff-delta">${t.environmental_delta}</div>` : ''}
            </div>
        `).join('')}`;
}

function renderAgentReasoning(reasoning) {
    const container = document.getElementById('agentReasoning');
    if (!container || !reasoning) return;

    const agents = Object.entries(reasoning);
    if (!agents.length) return;

    container.innerHTML = `
        <h2 class="section-title">Agent Reasoning</h2>
        ${agents.map(([name, output]) => `
            <div class="agent-panel">
                <div class="agent-panel-header" onclick="this.parentElement.classList.toggle('open')">
                    <span class="agent-name">${name}</span>
                    <span class="agent-toggle">&#9660;</span>
                </div>
                <div class="agent-panel-body">
                    <pre class="agent-output">${typeof output === 'string' ? output : JSON.stringify(output, null, 2)}</pre>
                </div>
            </div>
        `).join('')}`;
}

function renderDedalusBadge() {
    const container = document.getElementById('dedalusBadge');
    if (!container) return;

    container.innerHTML = `
        <div class="dedalus-badge">
            <span class="dedalus-icon">&#9889;</span>
            Powered by Dedalus Labs AI Agent Swarm
        </div>`;
}
