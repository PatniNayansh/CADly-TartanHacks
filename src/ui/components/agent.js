/**
 * Agent UI - File upload + SSE streaming for Dedalus-powered analysis
 */

let uploadedFile = null;

// ==================== File Upload ====================

const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');
const filePreview = document.getElementById('filePreview');

// Click to upload
dropzone.addEventListener('click', () => fileInput.click());

// Drag & drop
dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
});

dropzone.addEventListener('dragleave', () => {
    dropzone.classList.remove('dragover');
});

dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');

    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFileUpload(files[0]);
    }
});

// File input change
fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFileUpload(e.target.files[0]);
    }
});

function handleFileUpload(file) {
    const ext = file.name.split('.').pop().toLowerCase();
    if (!['stl', 'obj'].includes(ext)) {
        alert('Please upload STL or OBJ files only');
        return;
    }

    uploadedFile = file;
    filePreview.innerHTML = `
        <div class="file-info">
            <span class="file-name">${file.name}</span>
            <span class="file-size">${(file.size / 1024).toFixed(1)} KB</span>
            <button onclick="clearFile()" class="clear-btn">×</button>
        </div>
    `;
    filePreview.classList.remove('hidden');
}

function clearFile() {
    uploadedFile = null;
    filePreview.innerHTML = '';
    filePreview.classList.add('hidden');
    fileInput.value = '';
}

// Make clearFile global for onclick handler
window.clearFile = clearFile;

// ==================== Model Strategy Selection ====================

const strategySelect = document.getElementById('strategySelect');
const customModels = document.getElementById('customModels');
const extractionModelSelect = document.getElementById('extractionModelSelect');
const reasoningModelSelect = document.getElementById('reasoningModelSelect');
const extractionCost = document.getElementById('extractionCost');
const reasoningCost = document.getElementById('reasoningCost');
const totalCost = document.getElementById('totalCost');

// Cost per 1M tokens (approximate as of 2026)
const MODEL_COSTS = {
    'google/gemini-2.0-flash-exp': 0.10,           // Cheapest
    'anthropic/claude-haiku-4-5-20251001': 0.40,   // Fast & cheap
    'anthropic/claude-sonnet-4-5-20250929': 3.00,  // Balanced
    'claude-opus-4-5-20251101': 15.00              // Most powerful
};

// Estimated token usage per phase
const EXTRACTION_TOKENS = 2000;
const REASONING_TOKENS = 5000;

// Show/hide custom models section
strategySelect.addEventListener('change', () => {
    if (strategySelect.value === 'custom') {
        customModels.classList.remove('hidden');
    } else {
        customModels.classList.add('hidden');
    }
});

// Update cost estimates when models change
extractionModelSelect.addEventListener('change', updateCostEstimates);
reasoningModelSelect.addEventListener('change', updateCostEstimates);

function updateCostEstimates() {
    const extractionModel = extractionModelSelect.value;
    const reasoningModel = reasoningModelSelect.value;

    const extractionCostVal = (EXTRACTION_TOKENS / 1_000_000) * MODEL_COSTS[extractionModel];
    const reasoningCostVal = (REASONING_TOKENS / 1_000_000) * MODEL_COSTS[reasoningModel];
    const totalCostVal = extractionCostVal + reasoningCostVal;

    extractionCost.textContent = `~$${extractionCostVal.toFixed(4)}`;
    reasoningCost.textContent = `~$${reasoningCostVal.toFixed(4)}`;
    totalCost.textContent = `$${totalCostVal.toFixed(4)}`;
}

// Initialize cost estimates
updateCostEstimates();

// ==================== Agent Analysis ====================

const analyzeAgentBtn = document.getElementById('analyzeAgentBtn');
const agentProgress = document.getElementById('agentProgress');
const phaseList = document.getElementById('phaseList');
const findingsStream = document.getElementById('findingsStream');

analyzeAgentBtn.addEventListener('click', runAgentAnalysis);

async function runAgentAnalysis() {
    const useFusion = document.getElementById('useFusion').checked;
    const machineText = document.getElementById('machineText').value;
    const process = document.getElementById('processSelect').value;
    const strategy = strategySelect.value;

    // Validation
    if (!uploadedFile && !useFusion) {
        alert('Please upload a file or check "Use live Fusion 360"');
        return;
    }

    // Show progress UI
    agentProgress.classList.remove('hidden');
    phaseList.innerHTML = '';
    findingsStream.innerHTML = '';

    // Disable button during analysis
    analyzeAgentBtn.disabled = true;
    analyzeAgentBtn.textContent = 'Analyzing...';

    // Build FormData
    const formData = new FormData();
    if (uploadedFile) {
        formData.append('file', uploadedFile);
    }
    formData.append('machine_text', machineText);
    formData.append('process', process);
    formData.append('quantity', '1');
    formData.append('use_fusion', useFusion ? 'true' : 'false');
    formData.append('strategy', strategy);

    // Add custom model selections if custom strategy
    if (strategy === 'custom') {
        formData.append('extraction_model', extractionModelSelect.value);
        formData.append('reasoning_model', reasoningModelSelect.value);
    }

    try {
        // Make POST request
        const response = await fetch('/api/agent/analyze', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        // Set up SSE event listener
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            // Process complete SSE messages
            const lines = buffer.split('\n\n');
            buffer = lines.pop() || ''; // Keep incomplete message in buffer

            for (const line of lines) {
                if (line.trim()) {
                    processSSEMessage(line);
                }
            }
        }

    } catch (error) {
        console.error('Agent analysis failed:', error);
        alert(`Analysis failed: ${error.message}`);
    } finally {
        // Re-enable button
        analyzeAgentBtn.disabled = false;
        analyzeAgentBtn.innerHTML = '<span class="btn-icon">🚀</span>Analyze with AI Agent';
    }
}

function processSSEMessage(message) {
    const lines = message.split('\n');
    let eventType = 'message';
    let eventData = '';

    for (const line of lines) {
        if (line.startsWith('event: ')) {
            eventType = line.substring(7).trim();
        } else if (line.startsWith('data: ')) {
            eventData = line.substring(6).trim();
        }
    }

    if (!eventData) return;

    try {
        const data = JSON.parse(eventData);

        switch (eventType) {
            case 'phase':
                addPhaseIndicator(data);
                break;
            case 'model_handoff':
                addModelHandoff(data);
                break;
            case 'finding':
                addFinding(data);
                break;
            case 'cost':
                // Handle cost events if needed
                console.log('Cost event:', data);
                break;
            case 'recommendation':
                // Handle recommendation events if needed
                console.log('Recommendation event:', data);
                break;
            case 'final':
                displayFinalReport(data.data);
                break;
            case 'error':
                console.error('Agent error:', data);
                alert(`Analysis error: ${data.message}`);
                break;
        }
    } catch (e) {
        console.error('Failed to parse SSE data:', e, eventData);
    }
}

function addPhaseIndicator(event) {
    // Find existing phase item or create new one
    let phaseEl = document.querySelector(`[data-phase="${event.phase}"]`);

    if (!phaseEl) {
        phaseEl = document.createElement('div');
        phaseEl.className = 'phase-item';
        phaseEl.dataset.phase = event.phase;
        phaseList.appendChild(phaseEl);
    }

    const icon = event.progress >= 1.0 || event.type === 'final' ? '✓' : '⏳';
    const isComplete = event.progress >= 1.0 || event.type === 'final';

    phaseEl.innerHTML = `
        <span class="phase-icon">${icon}</span>
        <span class="phase-name">${event.message}</span>
        <span class="phase-progress">${(event.progress * 100).toFixed(0)}%</span>
    `;

    if (isComplete) {
        phaseEl.classList.add('complete');
    }
}

function addModelHandoff(event) {
    const handoffEl = document.createElement('div');
    handoffEl.className = 'phase-item model-handoff';
    handoffEl.dataset.phase = event.phase;

    const icon = '🔄';
    handoffEl.innerHTML = `
        <span class="phase-icon">${icon}</span>
        <span class="phase-name">${event.message}</span>
        <span class="phase-progress">${(event.progress * 100).toFixed(0)}%</span>
    `;

    phaseList.appendChild(handoffEl);

    // Add visual highlight animation
    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            handoffEl.classList.add('highlight');
            setTimeout(() => handoffEl.classList.remove('highlight'), 1000);
        });
    });
}

function addFinding(event) {
    if (!event.data) return;

    const findingEl = document.createElement('div');
    const severity = event.data.severity || 'warning';
    findingEl.className = `finding-card severity-${severity}`;

    findingEl.innerHTML = `
        <div class="finding-header">
            <span class="rule-id">${event.data.rule_id || 'UNKNOWN'}</span>
            <span class="severity-badge ${severity}">${severity}</span>
        </div>
        <p class="finding-message">${event.data.message || 'No message'}</p>
        <div class="finding-details">
            Current: ${event.data.current_value} | Required: ${event.data.required_value}
        </div>
    `;

    findingsStream.appendChild(findingEl);

    // Slide-in animation
    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            findingEl.classList.add('visible');
        });
    });
}

function displayFinalReport(report) {
    console.log('Final report received:', report);

    // Hide agent progress after delay
    setTimeout(() => {
        agentProgress.classList.add('hidden');
    }, 2000);

    // === POPULATE SUMMARY CARD ===
    const summary = document.getElementById('summary');
    const partName = document.getElementById('partName');
    const processRec = document.getElementById('processRecommendation');
    const totalViolations = document.getElementById('totalViolations');
    const criticalCount = document.getElementById('criticalCount');
    const warningCount = document.getElementById('warningCount');

    const findingsCount = report.findings?.length || 0;
    const critical = report.blocking_issues?.length || 0;
    const warnings = report.warnings?.length || 0;

    partName.textContent = report.part_name || 'Analysis Complete';
    processRec.textContent = report.recommended_process?.toUpperCase() || 'Unknown';
    processRec.className = `badge ${report.is_manufacturable ? 'success' : 'warning'}`;
    totalViolations.textContent = findingsCount;
    criticalCount.textContent = critical;
    warningCount.textContent = warnings;
    summary.style.display = 'block';

    // === POPULATE VIOLATIONS LIST ===
    // Convert findings to violation format and use existing renderer
    const violations = report.findings.map(finding => ({
        rule_id: finding.rule_id,
        severity: finding.severity,
        message: finding.message,
        current_value: finding.current_value,
        required_value: finding.required_value,
        fixable: finding.fixable,
        feature_id: finding.feature_id || 'unknown',
        process: finding.process,
        location: null  // Agent doesn't provide location data
    }));

    // Use the existing renderViolations function from violations.js
    if (typeof renderViolations === 'function') {
        renderViolations(violations);
    } else {
        // Fallback if renderViolations not loaded
        const violationsSection = document.getElementById('violationsSection');
        const violationsList = document.getElementById('violationsList');

        if (findingsCount > 0) {
            violationsList.innerHTML = '';
            violations.forEach(v => {
                const card = document.createElement('div');
                card.className = `violation-card ${v.severity}`;
                card.innerHTML = `
                    <div class="violation-header">
                        <span class="violation-id">${v.rule_id}</span>
                        <span class="severity-badge severity-${v.severity}">${v.severity}</span>
                    </div>
                    <p class="violation-message">${v.message}</p>
                    <div class="violation-values">
                        <span>Current: <strong>${v.current_value.toFixed(2)}mm</strong></span>
                        <span>Required: <strong>${v.required_value.toFixed(2)}mm</strong></span>
                    </div>
                    ${v.fixable ? `
                        <div class="fix-action">
                            <button class="btn-fix" onclick="applyFix('${v.rule_id}', '${v.feature_id}', ${v.required_value}, ${v.current_value})">Auto-Fix</button>
                        </div>
                    ` : ''}
                `;
                violationsList.appendChild(card);
            });
            violationsSection.style.display = 'block';
        } else {
            violationsSection.style.display = 'none';
        }
    }

    // === POPULATE COST TABLE ===
    const costSection = document.getElementById('costSection');
    const costTable = document.getElementById('costTable');

    if (report.cost_estimates && report.cost_estimates.length > 0) {
        costTable.innerHTML = `
            <table class="cost-comparison-table">
                <thead>
                    <tr>
                        <th>Process</th>
                        <th>Material</th>
                        <th>Machine Time</th>
                        <th>Setup</th>
                        <th>Total</th>
                    </tr>
                </thead>
                <tbody>
                    ${report.cost_estimates.map(cost => `
                        <tr>
                            <td>${cost.process.toUpperCase()}</td>
                            <td>$${cost.material_cost.toFixed(2)}</td>
                            <td>$${cost.machine_time_cost.toFixed(2)}</td>
                            <td>$${cost.setup_cost.toFixed(2)}</td>
                            <td><strong>$${cost.total.toFixed(2)}</strong></td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
        costSection.style.display = 'block';
    }

    // Hide empty state
    document.getElementById('emptyState').style.display = 'none';

    // === SHOW SUCCESS NOTIFICATION ===
    let message = `Analysis complete!

Findings: ${findingsCount}
Manufacturable: ${report.is_manufacturable ? 'Yes' : 'No'}
Recommended Process: ${report.recommended_process?.toUpperCase() || 'Unknown'}`;

    // Add cost savings if available
    if (report.cost_analysis) {
        const costAnalysis = report.cost_analysis;
        message += `

Strategy: ${costAnalysis.strategy.toUpperCase()}
Total Cost: $${costAnalysis.total_cost.toFixed(4)}`;

        if (costAnalysis.savings > 0) {
            message += `
Savings: $${costAnalysis.savings.toFixed(4)} (${costAnalysis.savings_percent.toFixed(1)}%)`;
        }
    }

    message += `

Results displayed below!`;

    alert(message);
}

console.log('Agent UI loaded');
