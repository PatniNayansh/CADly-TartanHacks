// Cadly v2 — Decision Summary Panel
// Consolidates analysis + cost + sustainability into one "TL;DR" for judges.

function renderDecisionSummary(analysis, cost, sustainability) {
    const container = document.getElementById('decisionSummary');
    if (!container) return;

    // Need at least analysis data
    if (!analysis) {
        container.style.display = 'none';
        return;
    }

    container.style.display = 'block';

    // Extract key data points
    const criticalCount = analysis.critical_count || 0;
    const warningCount = analysis.warning_count || 0;
    const totalViolations = analysis.violation_count || 0;
    const recProcess = analysis.recommended_process || 'N/A';

    // Cost recommendation
    let cheapestProcess = 'N/A';
    let cheapestCost = null;
    if (cost && cost.estimates) {
        const sorted = [...cost.estimates].sort((a, b) => a.total_cost - b.total_cost);
        if (sorted.length > 0) {
            cheapestProcess = sorted[0].process;
            cheapestCost = sorted[0].total_cost;
        }
    }

    // Sustainability
    let greenScore = null;
    let greenProcess = 'N/A';
    let greenGrade = '';
    if (sustainability && sustainability.green_scores && sustainability.green_scores.length > 0) {
        const best = sustainability.green_scores[0]; // Already sorted desc
        greenScore = best.score;
        greenProcess = best.process;
        greenGrade = best.grade;
    }

    // Build recommendation sentence
    const recSentence = buildRecommendation(recProcess, cheapestProcess, cheapestCost, greenProcess, greenScore, criticalCount, warningCount);

    // Status indicator
    const statusClass = criticalCount > 0 ? 'critical' :
                         warningCount > 0 ? 'warning' : 'good';
    const statusText = criticalCount > 0 ? 'Issues Found' :
                        warningCount > 0 ? 'Warnings Only' : 'Ready to Manufacture';

    container.innerHTML = `
        <div class="decision-card ${statusClass}">
            <div class="decision-status">
                <span class="decision-status-dot ${statusClass}"></span>
                <span class="decision-status-text">${statusText}</span>
            </div>
            <div class="decision-recommendation">${recSentence}</div>
            <div class="decision-metrics">
                <div class="decision-metric">
                    <span class="decision-metric-value">${totalViolations}</span>
                    <span class="decision-metric-label">Issues</span>
                </div>
                ${cheapestCost !== null ? `
                <div class="decision-metric">
                    <span class="decision-metric-value">$${cheapestCost.toFixed(2)}</span>
                    <span class="decision-metric-label">Best Cost (${cheapestProcess})</span>
                </div>` : ''}
                ${greenScore !== null ? `
                <div class="decision-metric">
                    <span class="decision-metric-value ${greenScore >= 70 ? 'green' : greenScore >= 40 ? 'amber' : 'red'}">${greenScore}/100</span>
                    <span class="decision-metric-label">Green Score (${greenProcess})</span>
                </div>` : ''}
            </div>
        </div>`;
}

function buildRecommendation(recProcess, cheapestProcess, cheapestCost, greenProcess, greenScore, criticalCount, warningCount) {
    const parts = [];

    // Process recommendation
    if (recProcess && recProcess !== 'N/A') {
        parts.push(`Cadly recommends <strong>${recProcess}</strong> for this part.`);
    }

    // Cost note
    if (cheapestCost !== null) {
        if (cheapestProcess === recProcess) {
            parts.push(`Estimated cost: <strong>$${cheapestCost.toFixed(2)}</strong>.`);
        } else {
            parts.push(`Cheapest option: <strong>${cheapestProcess}</strong> at <strong>$${cheapestCost.toFixed(2)}</strong>.`);
        }
    }

    // Green score note
    if (greenScore !== null) {
        const greenColor = greenScore >= 70 ? 'good' : greenScore >= 40 ? 'moderate' : 'poor';
        parts.push(`Sustainability: <strong>${greenProcess}</strong> scores ${greenScore}/100 (${greenColor}).`);
    }

    // Violation summary
    if (criticalCount > 0) {
        parts.push(`<strong>${criticalCount} critical</strong> issue${criticalCount > 1 ? 's' : ''} must be fixed before manufacturing.`);
    } else if (warningCount > 0) {
        parts.push(`${warningCount} warning${warningCount > 1 ? 's' : ''} found — review recommended.`);
    } else {
        parts.push('No issues detected — ready to manufacture.');
    }

    return parts.join(' ');
}
