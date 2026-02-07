// Machine + Material Recommendation UI

async function loadRecommendations() {
    const process = document.getElementById('recProcess').value;
    const btn = document.getElementById('recBtn');
    const placeholder = document.getElementById('recPlaceholder');
    const results = document.getElementById('recResults');

    btn.disabled = true;
    btn.textContent = 'Loading...';
    results.innerHTML = '';
    placeholder.style.display = 'none';

    try {
        const [machineResp, materialResp] = await Promise.all([
            apiGet(`/api/machines?process=${process}`),
            apiGet(`/api/materials?process=${process}`),
        ]);

        let html = '';

        // Machine section
        html += '<div class="section"><h2 class="section-title">Recommended Machines</h2>';
        if (machineResp.success && machineResp.data.machines.length > 0) {
            html += renderMachines(machineResp.data.machines);
        } else {
            html += '<p class="rec-empty">No machines found for this process.</p>';
        }
        html += '</div>';

        // Material section
        html += '<div class="section"><h2 class="section-title">Recommended Materials</h2>';
        if (materialResp.success && materialResp.data.materials.length > 0) {
            html += renderMaterials(materialResp.data.materials);
        } else {
            html += '<p class="rec-empty">No materials found for this process.</p>';
        }
        html += '</div>';

        results.innerHTML = html;
    } catch (err) {
        results.innerHTML = `<div class="error-msg">Failed to load recommendations: ${err.message}</div>`;
        placeholder.style.display = 'block';
    } finally {
        btn.disabled = false;
        btn.textContent = 'Get Recommendations';
    }
}

function renderMachines(machines) {
    return machines.map((entry, i) => {
        const m = entry.machine;
        const scoreColor = entry.score >= 7 ? 'var(--accent)' : entry.score >= 5 ? '#f0ad4e' : '#e74c3c';
        const fitBadge = entry.fits_part
            ? '<span class="rec-badge rec-badge-green">Fits Part</span>'
            : '<span class="rec-badge rec-badge-red">Too Small</span>';
        const rank = i + 1;

        const reasons = entry.reasons
            .filter(r => !r.startsWith('Best for:'))
            .map(r => `<li>${r}</li>`).join('');
        const bestFor = (m.best_for || []).map(b => `<span class="rec-tag">${b}</span>`).join('');
        const warnings = (entry.warnings || []).map(w => `<li class="rec-warning-item">${w}</li>`).join('');

        const bv = m.build_volume;
        const specs = [
            `${bv.x} x ${bv.y} x ${bv.z} mm`,
            `Tolerance: ${m.tolerance_mm}mm`,
            m.axes ? `${m.axes}-axis` : null,
            `$${m.price_usd.toLocaleString()}`,
        ].filter(Boolean).join(' &middot; ');

        return `
        <div class="rec-card ${!entry.fits_part ? 'rec-card-dimmed' : ''}" style="animation-delay: ${i * 60}ms">
            <div class="rec-card-header">
                <div class="rec-rank">#${rank}</div>
                <div class="rec-card-title">
                    <strong>${m.name}</strong>
                    <span class="rec-manufacturer">${m.manufacturer}</span>
                </div>
                <div class="rec-score" style="color: ${scoreColor}">${entry.score.toFixed(1)}</div>
            </div>
            <div class="rec-specs">${specs}</div>
            <div class="rec-ratings">
                <div class="rec-rating-bar">
                    <span class="rec-rating-label">Speed</span>
                    <div class="rec-bar-track"><div class="rec-bar-fill" style="width: ${m.speed_rating * 10}%"></div></div>
                    <span class="rec-rating-val">${m.speed_rating}/10</span>
                </div>
                <div class="rec-rating-bar">
                    <span class="rec-rating-label">Precision</span>
                    <div class="rec-bar-track"><div class="rec-bar-fill rec-bar-precision" style="width: ${m.precision_rating * 10}%"></div></div>
                    <span class="rec-rating-val">${m.precision_rating}/10</span>
                </div>
            </div>
            ${fitBadge}
            ${bestFor ? `<div class="rec-tags">${bestFor}</div>` : ''}
            ${reasons ? `<ul class="rec-reasons">${reasons}</ul>` : ''}
            ${warnings ? `<ul class="rec-warnings">${warnings}</ul>` : ''}
        </div>`;
    }).join('');
}

function renderMaterials(materials) {
    return materials.map((entry, i) => {
        const mat = entry.material;
        const scoreColor = entry.score >= 5 ? 'var(--accent)' : entry.score >= 3 ? '#f0ad4e' : '#e74c3c';
        const rank = i + 1;

        // Spider chart as horizontal bars
        const spider = entry.spider_chart || {};
        const spiderBars = Object.entries(spider).map(([axis, val]) => {
            const label = axis.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
            const pct = (val / 10) * 100;
            return `
            <div class="rec-rating-bar">
                <span class="rec-rating-label">${label}</span>
                <div class="rec-bar-track"><div class="rec-bar-fill rec-bar-material" style="width: ${pct}%"></div></div>
                <span class="rec-rating-val">${val.toFixed(1)}</span>
            </div>`;
        }).join('');

        const highlights = (entry.highlights || []).map(h => `<span class="rec-tag rec-tag-highlight">${h}</span>`).join('');
        const advantages = (mat.advantages || []).slice(0, 3).map(a => `<li>${a}</li>`).join('');
        const disadvantages = (mat.disadvantages || []).slice(0, 2).map(d => `<li class="rec-warning-item">${d}</li>`).join('');
        const uses = (mat.typical_uses || []).map(u => `<span class="rec-tag">${u}</span>`).join('');

        return `
        <div class="rec-card" style="animation-delay: ${i * 60}ms">
            <div class="rec-card-header">
                <div class="rec-rank">#${rank}</div>
                <div class="rec-card-title">
                    <strong>${mat.name}</strong>
                    <span class="rec-manufacturer">${mat.category}</span>
                </div>
                <div class="rec-score" style="color: ${scoreColor}">${entry.score.toFixed(1)}</div>
            </div>
            ${highlights ? `<div class="rec-tags">${highlights}</div>` : ''}
            <div class="rec-spider">${spiderBars}</div>
            ${advantages ? `<ul class="rec-reasons">${advantages}</ul>` : ''}
            ${disadvantages ? `<ul class="rec-warnings">${disadvantages}</ul>` : ''}
            ${uses ? `<div class="rec-tags" style="margin-top: 8px">${uses}</div>` : ''}
        </div>`;
    }).join('');
}
