// ─────────────────────────────────────────────────────────────────────────────
// Third Eye — AI Forensic System  |  script.js  v4
// ─────────────────────────────────────────────────────────────────────────────
const API_URL = window.location.origin;

let generateFile  = null;
let recognizeFile = null;
let fabricCanvas  = null;

// Tracking filenames returned from server for pipeline chaining
let _compositeFilename = null;   // last composite filename (describe tab)
let _sketchFilename    = null;   // last photo-sketch filename (generate tab)

// ══════════════════════════════════════════════════════════════
// BOOT
// ══════════════════════════════════════════════════════════════
window.onload = async () => {
    try { initCanvas(); } catch(e) { console.warn('Canvas init skipped:', e.message); }
    await checkAuth();
};

// ══════════════════════════════════════════════════════════════
// AUTHENTICATION
// ══════════════════════════════════════════════════════════════
async function checkAuth() {
    try {
        const res = await fetch(`${API_URL}/api/me`, { credentials: 'include' }).then(r => r.json());
        if (res.logged_in) {
            document.getElementById('auth-modal').classList.remove('active');
            document.getElementById('app-layout').classList.add('visible');
            document.getElementById('current-agent').textContent = res.username;
            document.getElementById('current-role').textContent  = res.role;

            if (res.role === 'admin') {
                document.querySelectorAll('.admin-only').forEach(el => el.removeAttribute('style'));
                loadAdminSuspects();
            } else {
                document.querySelectorAll('.admin-only').forEach(el => el.style.display = 'none');
            }
            fetchStatus();
        } else {
            document.getElementById('auth-modal').classList.add('active');
            document.getElementById('app-layout').classList.remove('visible');
        }
    } catch (err) {
        showToast('Backend offline: ' + err.message, 'error');
    }
}

async function handleAuth(type) {
    const user = document.getElementById('auth-user').value;
    const pass = document.getElementById('auth-pass').value;
    if (!user || !pass) { showToast('Enter credentials', 'error'); return; }

    try {
        const res = await fetch(`${API_URL}/api/${type}`, {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: user, password: pass })
        }).then(r => r.json());

        if (res.success) {
            showToast(res.message || 'Authorized', 'success');
            await checkAuth();
        } else {
            showToast(res.error || 'Authentication failed', 'error');
        }
    } catch(err) {
        showToast('Error: ' + err.message, 'error');
    }
}

async function logout() {
    await fetch(`${API_URL}/api/logout`, { method: 'POST', credentials: 'include' });
    document.getElementById('auth-modal').classList.add('active');
    document.getElementById('app-layout').classList.remove('visible');
    document.getElementById('current-agent').textContent = 'Unknown';
    document.getElementById('current-role').textContent  = 'Guest';
}

// ══════════════════════════════════════════════════════════════
// TAB NAVIGATION
// ══════════════════════════════════════════════════════════════
document.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', e => {
        document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

        const id = e.currentTarget.getAttribute('data-tab');
        e.currentTarget.classList.add('active');
        document.getElementById(id).classList.add('active');

        if (id === 'tab-database') fetchStatus();
        if (id === 'tab-admin')    loadAdminSuspects();
        if (id === 'tab-canvas' && fabricCanvas) fabricCanvas.renderAll();
    });
});

// ══════════════════════════════════════════════════════════════
// PIPELINE 1b — DESCRIBE SUSPECT → FORENSIC COMPOSITE
// ══════════════════════════════════════════════════════════════
async function generateComposite() {
    const btn    = document.getElementById('describe-btn');
    const loader = document.getElementById('describe-loader');
    const text   = btn.querySelector('.btn-text');

    text.style.display = 'none';
    loader.classList.remove('hidden');

    const attrs = {
        age:          document.getElementById('d-age').value         || '35',
        gender:       document.getElementById('d-gender').value      || '',
        face_shape:   document.getElementById('d-face-shape').value  || 'oval',
        skin_tone:    document.getElementById('d-skin').value        || 'medium',
        eyes:         document.getElementById('d-eyes').value        || '',
        eyebrows:     document.getElementById('d-brows').value       || '',
        nose:         document.getElementById('d-nose').value        || '',
        lips:         document.getElementById('d-lips').value        || '',
        hair:         document.getElementById('d-hair').value        || '',
        facial_hair:  document.getElementById('d-facial-hair').value || '',
        marks:        document.getElementById('d-marks').value       || '',
        accessories:  document.getElementById('d-accessories').value || '',
    };

    try {
        const res = await fetch(`${API_URL}/api/describe-sketch`, {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(attrs)
        }).then(r => r.json());

        if (res.success) {
            _compositeFilename = res.filename;
            const ts = Date.now();
            document.getElementById('describe-img').src = `${API_URL}${res.sketch_url}?t=${ts}`;
            document.getElementById('describe-placeholder').classList.add('hidden');
            document.getElementById('describe-result').classList.remove('hidden');
            document.getElementById('enhanced-result').classList.add('hidden');
            showToast('Forensic composite generated!', 'success');
        } else {
            throw new Error(res.error);
        }
    } catch(err) {
        showToast(err.message, 'error');
    } finally {
        text.style.display = '';
        loader.classList.add('hidden');
    }
}

async function enhanceComposite() {
    if (!_compositeFilename) { showToast('Generate a composite first', 'error'); return; }

    const btnText = document.getElementById('enhance-btn-text');
    const loader  = document.getElementById('enhance-loader');
    btnText.style.display = 'none';
    loader.classList.remove('hidden');

    try {
        const fd = new FormData();
        fd.append('filename', _compositeFilename);

        const res = await fetch(`${API_URL}/api/enhance-sketch`, {
            method: 'POST',
            credentials: 'include',
            body: fd
        }).then(r => r.json());

        if (res.success) {
            const ts = Date.now();
            document.getElementById('enhanced-img').src = `${API_URL}${res.enhanced_url}?t=${ts}`;
            document.getElementById('enhanced-result').classList.remove('hidden');
            showToast('GAN enhancement complete!', 'success');
        } else {
            throw new Error(res.error);
        }
    } catch(err) {
        showToast(err.message, 'error');
    } finally {
        btnText.style.display = '';
        loader.classList.add('hidden');
    }
}

function matchComposite() {
    if (!_compositeFilename) { showToast('Generate a composite first', 'error'); return; }
    // Switch to recognition tab and load the composite image for matching
    document.querySelector('[data-tab="tab-recognize"]').click();
    showToast('Upload the composite image manually in the Match tab, or use "Match AI" from the canvas.', 'info');
}

function resetComposite() {
    _compositeFilename = null;
    document.getElementById('describe-placeholder').classList.remove('hidden');
    document.getElementById('describe-result').classList.add('hidden');
    document.getElementById('enhanced-result').classList.add('hidden');
}

// ══════════════════════════════════════════════════════════════
// PIPELINE 1 — PHOTO → SKETCH
// ══════════════════════════════════════════════════════════════
async function generateSketch() {
    if (!generateFile) { showToast('Select an image', 'error'); return; }

    const text   = document.querySelector('#gen-preview .btn-text');
    const loader = document.getElementById('gen-loader');
    text.style.display = 'none';
    loader.classList.remove('hidden');

    const fd = new FormData();
    fd.append('file', generateFile);

    try {
        const res = await fetch(`${API_URL}/api/generate-sketch`, {
            method: 'POST',
            body: fd,
            credentials: 'include'
        }).then(r => r.json());

        if (res.success) {
            const ts = Date.now();
            document.getElementById('gen-preview').classList.add('hidden');
            document.getElementById('gen-results').classList.remove('hidden');
            document.getElementById('gen-res-orig').src   = `${API_URL}${res.original_url}?t=${ts}`;
            document.getElementById('gen-res-sketch').src  = `${API_URL}${res.sketch_url}?t=${ts}`;
            // Store sketch filename for the enhance button
            _sketchFilename = res.sketch_url.split('/').pop();
            document.getElementById('gen-enhanced-result').classList.add('hidden');
            showToast('Sketch generated!', 'success');
            setTimeout(() => {
                document.getElementById('upload-gen').style.display = 'block';
                generateFile = null;
            }, 6000);
        } else {
            throw new Error(res.error);
        }
    } catch(err) {
        showToast(err.message, 'error');
    } finally {
        text.style.display = '';
        loader.classList.add('hidden');
    }
}

async function enhanceSketchResult() {
    if (!_sketchFilename) { showToast('Generate a sketch first', 'error'); return; }

    const btnText = document.getElementById('enhance-sketch-btn-text');
    const loader  = document.getElementById('enhance-sketch-loader');
    btnText.style.display = 'none';
    loader.classList.remove('hidden');

    try {
        const fd = new FormData();
        fd.append('filename', _sketchFilename);

        const res = await fetch(`${API_URL}/api/enhance-sketch`, {
            method: 'POST',
            credentials: 'include',
            body: fd
        }).then(r => r.json());

        if (res.success) {
            const ts = Date.now();
            document.getElementById('gen-enhanced-img').src = `${API_URL}${res.enhanced_url}?t=${ts}`;
            document.getElementById('gen-enhanced-result').classList.remove('hidden');
            showToast('GAN enhancement complete!', 'success');
        } else {
            throw new Error(res.error);
        }
    } catch(err) {
        showToast(err.message, 'error');
    } finally {
        btnText.style.display = '';
        loader.classList.add('hidden');
    }
}

// ══════════════════════════════════════════════════════════════
// PIPELINE 3 — SUSPECT MATCHING (HOG + Cosine Similarity)
// ══════════════════════════════════════════════════════════════
async function recognizeSuspect() {
    if (!recognizeFile) return;

    const text   = document.querySelector('#rec-preview .btn-text');
    const loader = document.getElementById('rec-loader');
    text.style.display = 'none';
    loader.classList.remove('hidden');

    const fd = new FormData();
    fd.append('file', recognizeFile);
    await executeMatch(fd);

    text.style.display = '';
    loader.classList.add('hidden');
}

async function recognizeFromCanvas() {
    if (!fabricCanvas) return;
    const loader = document.getElementById('canvas-loader');
    loader.classList.remove('hidden');

    document.querySelector('[data-tab="tab-recognize"]').click();
    const dataURL = fabricCanvas.toDataURL({ format: 'png', quality: 1.0 });
    const fd = new FormData();
    fd.append('base64_image', dataURL);
    await executeMatch(fd);

    loader.classList.add('hidden');
}

async function executeMatch(formData) {
    try {
        const res = await fetch(`${API_URL}/api/recognize-sketch`, {
            method: 'POST',
            body: formData,
            credentials: 'include'
        }).then(r => r.json());

        if (res.success) {
            const ts = Date.now();
            // Show hero cards
            document.getElementById('rec-preview').classList.add('hidden');
            document.getElementById('upload-rec').style.display = 'none';
            document.getElementById('rec-results').classList.remove('hidden');

            document.getElementById('rec-res-query').src = `${API_URL}${res.query_url}?t=${ts}`;
            document.getElementById('rec-res-match').src = res.match_url
                ? `${API_URL}${res.match_url}?t=${ts}`
                : `data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80"><rect width="80" height="80" fill="%23374151"/><text x="50%" y="55%" text-anchor="middle" fill="%236b7280" font-size="10">No Image</text></svg>`;

            document.getElementById('rec-match-name').textContent = (res.match_name || '—').replace(/_/g, ' ').toUpperCase();
            document.getElementById('rec-match-desc').textContent = res.description || '';
            document.getElementById('rec-confidence').textContent = `${res.confidence}%`;
            document.getElementById('rec-confidence').style.color =
                res.confidence >= 85 ? '#10b981' : (res.confidence >= 70 ? '#eab308' : '#ef4444');

            // Confidence tier badge
            const tier   = res.tier || 'NO RELIABLE MATCH';
            const badge  = document.getElementById('rec-tier-badge');
            badge.textContent = tier;
            badge.className = 'tier-badge ' +
                (tier.startsWith('HIGH') ? 'tier-high' : tier.startsWith('POSSIBLE') ? 'tier-possible' : 'tier-none');

            // Ranked list
            _renderRankedList(res.matches || [], ts);
            showToast('Match engine complete', 'success');

            setTimeout(() => {
                document.getElementById('upload-rec').style.display = 'block';
                recognizeFile = null;
            }, 10000);
        } else {
            throw new Error(res.error);
        }
    } catch(err) {
        showToast(err.message, 'error');
    }
}

function _renderRankedList(matches, ts) {
    const list = document.getElementById('ranked-list');
    list.innerHTML = '';
    if (!matches.length) { list.innerHTML = '<p style="color:var(--text-muted);">No candidates found.</p>'; return; }

    matches.forEach(m => {
        const tierClass = m.tier.startsWith('HIGH') ? 'tier-high' : m.tier.startsWith('POSSIBLE') ? 'tier-possible' : 'tier-none';
        const row = document.createElement('div');
        row.className = 'ranked-item';
        row.innerHTML = `
            <div class="rank-badge">#${m.rank}</div>
            <div class="rank-info">
                <strong>${(m.name || '').replace(/_/g,' ').toUpperCase()}</strong>
                <span style="font-size:0.8rem; color:var(--text-muted);">${m.description || 'No records'}</span>
            </div>
            <div class="rank-score">
                <span style="font-size:1.4rem; font-weight:800; color:${m.score>=85?'#10b981':m.score>=70?'#eab308':'#ef4444'}">${m.score}%</span>
                <span class="tier-badge ${tierClass}" style="font-size:0.65rem; margin-top:4px;">${m.tier}</span>
            </div>`;
        list.appendChild(row);
    });
}

// ══════════════════════════════════════════════════════════════
// FABRIC.JS CANVAS
// ══════════════════════════════════════════════════════════════
function initCanvas() {
    fabricCanvas = new fabric.Canvas('fabricCanvas', { backgroundColor: '#ffffff', preserveObjectStacking: true });
    loadCategoryAssets();
}

async function loadCategoryAssets() {
    const category = document.getElementById('asset-category').value;
    const grid     = document.getElementById('asset-grid');
    if (!grid) return;

    grid.innerHTML = '<div class="loader" style="margin:2rem auto;"></div>';

    try {
        const files = await fetch(`${API_URL}/api/assets/${category}`).then(r => r.json());
        grid.innerHTML = '';
        if (!files.length) {
            grid.innerHTML = '<p style="font-size:0.8rem; color:#bbb; grid-column:1/-1; text-align:center;">No designs found.</p>';
            return;
        }
        files.forEach(file => {
            const url = `${API_URL}/static/assets/${category}/${file}`;
            const img = document.createElement('img');
            img.src         = url;
            img.style.cssText = 'width:100%; cursor:pointer; background:rgba(255,255,255,0.9); border-radius:8px; padding:6px; border:2px solid transparent; transition:border-color 0.2s;';
            img.onmouseover = () => img.style.borderColor = '#8b5cf6';
            img.onmouseout  = () => img.style.borderColor = 'transparent';
            img.onclick     = () => addAssetToCanvas(url);
            img.onload      = () => grid.appendChild(img);
        });
    } catch(err) {
        grid.innerHTML = '<p style="color:#ef4444; font-size:0.8rem; grid-column:1/-1;">Failed to load assets</p>';
    }
}

function addAssetToCanvas(url) {
    if (!fabricCanvas) return;
    const opts = {
        left: 260, top: 210, originX: 'center', originY: 'center',
        transparentCorners: false, cornerColor: '#8b5cf6',
        cornerStrokeColor: '#ffffff', borderColor: '#8b5cf6',
        cornerSize: 10, padding: 5
    };

    if (url.toLowerCase().endsWith('.svg')) {
        fabric.loadSVGFromURL(url, (objects, options) => {
            const obj = fabric.util.groupSVGElements(objects, options);
            obj.set(opts);
            fabricCanvas.add(obj).setActiveObject(obj).renderAll();
        });
    } else {
        fabric.Image.fromURL(url, img => {
            img.set(opts);
            if (img.width > 200) img.scaleToWidth(200);
            fabricCanvas.add(img).setActiveObject(img).renderAll();
        }, { crossOrigin: 'anonymous' });
    }
}

function uploadToCanvas(e) {
    if (!fabricCanvas) return;
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = evt => {
        fabric.Image.fromURL(evt.target.result, img => {
            img.set({ left: 260, top: 210, originX: 'center', originY: 'center',
                      transparentCorners: false, cornerColor: '#8b5cf6', cornerSize: 10, padding: 5 });
            if (img.width > 200) img.scaleToWidth(200);
            fabricCanvas.add(img).setActiveObject(img).renderAll();
        });
    };
    reader.readAsDataURL(file);
    e.target.value = '';
}

function bringForward()  { const o = fabricCanvas?.getActiveObject(); if(o){ fabricCanvas.bringForward(o); fabricCanvas.renderAll(); } }
function sendBackward()  { const o = fabricCanvas?.getActiveObject(); if(o){ fabricCanvas.sendBackward(o); fabricCanvas.renderAll(); } }
function deleteSelected(){ const o = fabricCanvas?.getActiveObject(); if(o){ fabricCanvas.remove(o);      fabricCanvas.renderAll(); } }
function clearCanvas()   { if(fabricCanvas){ fabricCanvas.clear(); fabricCanvas.backgroundColor='#ffffff'; fabricCanvas.renderAll(); } }

// ══════════════════════════════════════════════════════════════
// DRAG & DROP / FILE PREVIEW
// ══════════════════════════════════════════════════════════════
function handleDrop(e, inputId) {
    e.preventDefault();
    const files = e.dataTransfer.files;
    if (!files.length) return;
    document.getElementById(inputId).files = files;
    if (inputId === 'gen-input')   handleFileSelect({ target: document.getElementById(inputId) }, 'gen-preview');
    else if (inputId === 'rec-input') handleFileSelect({ target: document.getElementById(inputId) }, 'rec-preview');
    else if (inputId === 'admin-s-file') document.getElementById('admin-file-name').textContent = files[0].name;
    e.currentTarget.classList.remove('dragover');
}

document.querySelectorAll('.upload-area').forEach(a => {
    a.addEventListener('dragover',  e => { e.preventDefault(); a.classList.add('dragover'); });
    a.addEventListener('dragleave', e => { e.preventDefault(); a.classList.remove('dragover'); });
});

function handleFileSelect(e, previewId) {
    const file = e.target.files[0];
    if (!file || !file.type.match('image.*')) { showToast('Images only.', 'error'); return; }
    const reader = new FileReader();
    reader.onload = evt => {
        if (previewId === 'gen-preview') {
            generateFile = file;
            document.getElementById('gen-img-preview').src = evt.target.result;
            document.getElementById('gen-preview').classList.remove('hidden');
            document.getElementById('gen-results').classList.add('hidden');
            document.getElementById('gen-enhanced-result').classList.add('hidden');
            document.getElementById('upload-gen').style.display = 'none';
        } else {
            recognizeFile = file;
            document.getElementById('rec-img-preview').src = evt.target.result;
            document.getElementById('rec-preview').classList.remove('hidden');
            document.getElementById('rec-results').classList.add('hidden');
            document.getElementById('upload-rec').style.display = 'none';
        }
    };
    reader.readAsDataURL(file);
}

// ══════════════════════════════════════════════════════════════
// ADMIN / STATUS
// ══════════════════════════════════════════════════════════════
async function fetchStatus() {
    try {
        const res = await fetch(`${API_URL}/api/status`).then(r => r.json());
        document.getElementById('stat-db-size').textContent = res.database_size;
        const el = document.getElementById('stat-trained');
        el.textContent   = res.is_trained ? 'Yes' : 'No';
        el.style.color   = res.is_trained ? '#10b981' : '#ef4444';
    } catch(err) {}
}

async function loadAdminSuspects() {
    try {
        const suspects = await fetch(`${API_URL}/api/admin/suspects`, { credentials: 'include' }).then(r => r.json());
        const list = document.getElementById('suspects-list');
        list.innerHTML = '';
        suspects.forEach(s => {
            const div = document.createElement('div');
            div.className = 'suspect-item';
            div.innerHTML = `
                <img src="${API_URL}/database/${s.filename}" onerror="this.src=''">
                <div class="suspect-details">
                    <h4>${s.name.replace(/_/g,' ').toUpperCase()}</h4>
                    <p>${s.description ? s.description.substring(0,50)+'...' : 'No record'}</p>
                </div>
                <button onclick="deleteSuspect(${s.id})" style="margin-left:auto; background:#ef4444; border:none; color:white; border-radius:6px; padding:0.3rem 0.8rem; cursor:pointer; font-size:0.8rem;">✕</button>`;
            list.appendChild(div);
        });
    } catch(err) { console.error('Admin load failed', err); }
}

async function deleteSuspect(id) {
    if (!confirm('Delete this suspect record?')) return;
    try {
        const res = await fetch(`${API_URL}/api/admin/suspects/${id}`, {
            method: 'DELETE',
            credentials: 'include'
        }).then(r => r.json());
        if (res.success) { showToast('Suspect removed.', 'success'); loadAdminSuspects(); fetchStatus(); }
    } catch(err) { showToast('Delete failed', 'error'); }
}

async function uploadSuspectAdmin() {
    const file = document.getElementById('admin-s-file').files[0];
    const name = document.getElementById('admin-s-name').value;
    const desc = document.getElementById('admin-s-desc').value;
    if (!file || !name) { showToast('Name and photo required', 'error'); return; }

    const fd = new FormData();
    fd.append('file', file);
    fd.append('name', name);
    fd.append('description', desc);

    try {
        const res = await fetch(`${API_URL}/api/admin/suspects`, {
            method: 'POST',
            body: fd,
            credentials: 'include'
        }).then(r => r.json());

        if (res.success) {
            showToast('Suspect added. HOG index rebuilt.', 'success');
            document.getElementById('admin-s-name').value  = '';
            document.getElementById('admin-s-desc').value  = '';
            document.getElementById('admin-file-name').textContent = '';
            document.getElementById('admin-s-file').value  = '';
            loadAdminSuspects();
            fetchStatus();
        }
    } catch(err) { showToast('Upload failed', 'error'); }
}

// ══════════════════════════════════════════════════════════════
// TOAST NOTIFICATIONS
// ══════════════════════════════════════════════════════════════
function showToast(msg, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = msg;
    container.appendChild(toast);
    setTimeout(() => { if (toast.parentElement) toast.remove(); }, 5000);
}
