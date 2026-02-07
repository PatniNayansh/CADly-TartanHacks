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

    // Hide agent progress
    setTimeout(() => {
        agentProgress.classList.add('hidden');
    }, 2000);

    // Show success message
    const findingsCount = report.findings?.length || 0;
    const isManufacturable = report.is_manufacturable ? 'Yes' : 'No';

    alert(`Analysis complete!

Findings: ${findingsCount}
Manufacturable: ${isManufacturable}
Recommended Process: ${report.recommended_process?.toUpperCase() || 'Unknown'}

See full report in console.`);

    // Could also populate existing tabs with report data here
    // For now, log to console for debugging
}

console.log('Agent UI loaded');
