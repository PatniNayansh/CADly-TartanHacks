// Agent UI Component - Fake Dedalus Interface
// This creates a realistic streaming AI analysis UI using local endpoints

class AgentUI {
    constructor() {
        this.eventSource = null;
        this.isAnalyzing = false;
        this.findings = [];

        // Bind methods
        this.handleAnalyzeClick = this.handleAnalyzeClick.bind(this);
        this.handleFileUpload = this.handleFileUpload.bind(this);

        // Initialize after DOM loads
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.init());
        } else {
            this.init();
        }
    }

    init() {
        // Get DOM elements
        this.analyzeBtn = document.getElementById('agentAnalyzeBtn');
        this.progressContainer = document.getElementById('agentProgress');
        this.findingsContainer = document.getElementById('agentFindings');
        this.fileInput = document.getElementById('agentFileInput');
        this.dropzone = document.getElementById('agentDropzone');
        this.machineInput = document.getElementById('machineText');
        this.processSelect = document.getElementById('agentProcessSelect');
        this.quantityInput = document.getElementById('quantityInput');
        this.useFusionCheckbox = document.getElementById('useFusionCheckbox');
        this.strategySelect = document.getElementById('strategySelect');

        // Attach event listeners
        if (this.analyzeBtn) {
            this.analyzeBtn.addEventListener('click', this.handleAnalyzeClick);
        }

        if (this.fileInput) {
            this.fileInput.addEventListener('change', this.handleFileUpload);
        }

        if (this.dropzone) {
            this.setupDropzone();
        }
    }

    setupDropzone() {
        // Prevent default drag behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            this.dropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            });
        });

        // Highlight dropzone when file is dragged over
        ['dragenter', 'dragover'].forEach(eventName => {
            this.dropzone.addEventListener(eventName, () => {
                this.dropzone.classList.add('drag-over');
            });
        });

        ['dragleave', 'drop'].forEach(eventName => {
            this.dropzone.addEventListener(eventName, () => {
                this.dropzone.classList.remove('drag-over');
            });
        });

        // Handle dropped files
        this.dropzone.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.fileInput.files = files;
                this.updateDropzoneText(files[0].name);
            }
        });

        // Click to upload
        this.dropzone.addEventListener('click', () => {
            this.fileInput.click();
        });
    }

    handleFileUpload(e) {
        const file = e.target.files[0];
        if (file) {
            this.updateDropzoneText(file.name);
        }
    }

    updateDropzoneText(filename) {
        const dropzoneText = this.dropzone.querySelector('p');
        if (dropzoneText) {
            dropzoneText.textContent = `📁 ${filename}`;
        }
    }

    async handleAnalyzeClick() {
        if (this.isAnalyzing) return;

        this.isAnalyzing = true;
        this.analyzeBtn.disabled = true;
        this.analyzeBtn.textContent = 'Analyzing...';
        this.findings = [];

        // Clear previous results
        this.findingsContainer.innerHTML = '';
        this.progressContainer.style.display = 'block';

        try {
            await this.startAnalysis();
        } catch (error) {
            console.error('Analysis failed:', error);
            this.showError(error.message);
        } finally {
            this.isAnalyzing = false;
            this.analyzeBtn.disabled = false;
            this.analyzeBtn.textContent = '🤖 Analyze with AI Agent';
        }
    }

    async startAnalysis() {
        // Build form data
        const formData = new FormData();

        // Add file if present
        if (this.fileInput.files.length > 0) {
            formData.append('file', this.fileInput.files[0]);
        }

        // Add other parameters
        formData.append('machine_text', this.machineInput.value);
        formData.append('process', this.processSelect.value);
        formData.append('quantity', this.quantityInput.value);
        formData.append('use_fusion', this.useFusionCheckbox.checked);
        formData.append('strategy', this.strategySelect.value);

        // Connect to SSE endpoint
        const response = await fetch('/api/agent/analyze', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`Analysis failed: ${response.statusText}`);
        }

        // Read SSE stream
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();

            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n\n');
            buffer = lines.pop(); // Keep incomplete message

            for (const line of lines) {
                if (line.trim()) {
                    this.handleSSEMessage(line);
                }
            }
        }
    }

    handleSSEMessage(message) {
        // Parse SSE format: "event: type\ndata: json"
        const eventMatch = message.match(/event: (\w+)/);
        const dataMatch = message.match(/data: (.+)/);

        if (!eventMatch || !dataMatch) return;

        const eventType = eventMatch[1];
        const data = JSON.parse(dataMatch[1]);

        switch (eventType) {
            case 'phase':
                this.handlePhaseEvent(data);
                break;
            case 'model_handoff':
                this.handleModelHandoff(data);
                break;
            case 'finding':
                this.handleFinding(data);
                break;
            case 'final':
                this.handleFinalReport(data);
                break;
        }
    }

    handlePhaseEvent(data) {
        const { phase, message, progress } = data;

        // Update progress bar
        const progressBar = document.getElementById('agentProgressBar');
        const progressText = document.getElementById('agentProgressText');

        if (progressBar) {
            progressBar.style.width = `${progress * 100}%`;
        }

        if (progressText) {
            progressText.textContent = message;
        }

        // Add phase indicator
        const phaseIndicator = document.getElementById(`phase-${phase}`);
        if (phaseIndicator) {
            if (progress === 1.0) {
                phaseIndicator.classList.add('complete');
            } else {
                phaseIndicator.classList.add('active');
            }
        }
    }

    handleModelHandoff(data) {
        const { message } = data;

        // Show model handoff message
        const progressText = document.getElementById('agentProgressText');
        if (progressText) {
            progressText.textContent = message;
            progressText.classList.add('model-handoff');
            setTimeout(() => {
                progressText.classList.remove('model-handoff');
            }, 500);
        }
    }

    handleFinding(data) {
        const finding = data.data;
        this.findings.push(finding);

        // Create finding card with slide-in animation
        const card = this.createFindingCard(finding);
        this.findingsContainer.appendChild(card);

        // Trigger animation
        setTimeout(() => {
            card.classList.add('slide-in');
        }, 10);
    }

    createFindingCard(finding) {
        const card = document.createElement('div');
        card.className = `finding-card severity-${finding.severity.toLowerCase()}`;

        const severityIcon = {
            'CRITICAL': '🔴',
            'WARNING': '🟡',
            'SUGGESTION': '🔵'
        }[finding.severity] || '⚪';

        card.innerHTML = `
            <div class="finding-header">
                <span class="finding-icon">${severityIcon}</span>
                <span class="finding-title">${finding.rule_id}: ${finding.message}</span>
            </div>
            <div class="finding-details">
                <div class="finding-stat">
                    <span class="stat-label">Current:</span>
                    <span class="stat-value">${finding.current_value.toFixed(2)}mm</span>
                </div>
                <div class="finding-stat">
                    <span class="stat-label">Required:</span>
                    <span class="stat-value">${finding.required_value.toFixed(2)}mm</span>
                </div>
            </div>
            ${finding.fix_available ? `
                <button class="btn-fix" onclick="window.agentFixViolation('${finding.rule_id}', '${finding.feature_id}', ${finding.required_value}, ${finding.current_value})">
                    Auto-Fix
                </button>
            ` : ''}
        `;

        return card;
    }

    handleFinalReport(data) {
        const report = data.data;

        // Hide progress
        this.progressContainer.style.display = 'none';

        // Update summary card (if exists in main UI)
        if (window.updateSummary) {
            window.updateSummary(report);
        }

        // Show cost estimates
        if (report.cost_estimates && window.updateCostTable) {
            window.updateCostTable(report.cost_estimates);
        }

        // Show success message
        const successMsg = document.createElement('div');
        successMsg.className = 'analysis-complete';
        successMsg.innerHTML = `
            <div class="success-icon">✅</div>
            <div class="success-text">
                <strong>Analysis Complete!</strong>
                <p>Found ${report.findings.length} issues. ${report.is_manufacturable ? 'Part is manufacturable.' : 'Please fix critical issues.'}</p>
            </div>
        `;
        this.findingsContainer.insertBefore(successMsg, this.findingsContainer.firstChild);
    }

    showError(message) {
        this.progressContainer.style.display = 'none';

        const errorCard = document.createElement('div');
        errorCard.className = 'finding-card severity-critical';
        errorCard.innerHTML = `
            <div class="finding-header">
                <span class="finding-icon">❌</span>
                <span class="finding-title">Analysis Failed</span>
            </div>
            <div class="finding-details">
                <p>${message}</p>
            </div>
        `;
        this.findingsContainer.appendChild(errorCard);
    }
}

// Initialize agent UI
const agentUI = new AgentUI();

// Global function for fixing violations from agent findings
window.agentFixViolation = async function(ruleId, featureId, targetValue, currentValue) {
    const btn = event.target;
    const originalText = btn.textContent;
    btn.textContent = 'Fixing...';
    btn.disabled = true;

    try {
        const API_BASE = window.location.origin;
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
            // Show success toast (if available)
            if (window.showToast) {
                window.showToast(data.message, 'success');
            }
            // Re-run analysis after fix
            if (window.runAnalysis) {
                setTimeout(window.runAnalysis, 1500);
            }
            // Also re-run agent analysis
            btn.textContent = '✓ Fixed!';
            setTimeout(() => {
                btn.parentElement.style.opacity = '0.5';
            }, 500);
        } else {
            if (window.showToast) {
                window.showToast(data.message || 'Fix failed', 'error');
            }
            btn.textContent = originalText;
            btn.disabled = false;
        }
    } catch (err) {
        if (window.showToast) {
            window.showToast(`Fix error: ${err.message}`, 'error');
        }
        btn.textContent = originalText;
        btn.disabled = false;
    }
};
