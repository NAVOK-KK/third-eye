// Dynamic API URL based on current page
const API_URL = window.location.origin;

let generateFile = null;
let recognizeFile = null;
let fabricCanvas = null;

// Initialize on Load
window.onload = async () => {
    initCanvas();
    // Check if user is already logged in
    await checkAuth();
};

// --- AUTHENTICATION ---
async function checkAuth() {
    try {
        const response = await fetch(`${API_URL}/api/me`, { credentials: 'include' });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const res = await response.json();
        
        if (res.logged_in) {
            document.getElementById('auth-modal').classList.remove('active');
            document.getElementById('app-layout').classList.add('visible');
            
            document.getElementById('current-agent').textContent = res.username;
            document.getElementById('current-role').textContent = res.role;
            
            if (res.role === 'admin') {
                document.querySelectorAll('.admin-only').forEach(el => {
                    el.style.display = '';
                    el.removeAttribute('style'); // Remove inline display:none
                });
                loadAdminSuspects();
            } else {
                document.querySelectorAll('.admin-only').forEach(el => el.style.display = 'none');
            }
            fetchStatus();
        } else {
            document.getElementById('auth-modal').classList.add('active');
            document.getElementById('app-layout').classList.remove('visible');
        }
    } catch (error) {
        console.error("Auth check failed:", error);
        showToast("Backend offline: " + error.message, "error");
    }
}

async function handleAuth(type) {
    const user = document.getElementById('auth-user').value;
    const pass = document.getElementById('auth-pass').value;
    if(!user || !pass) { showToast("Enter credentials", "error"); return; }
    
    try {
        const response = await fetch(`${API_URL}/api/${type}`, {
            method: 'POST',
            credentials: 'include',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username: user, password: pass})
        });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const res = await response.json();
        
        if (res.success) {
            showToast(res.message || "Authorized", "success");
            checkAuth();
        } else {
            showToast(res.error || "Authentication failed", "error");
        }
    } catch(err) {
        console.error("Login failed:", err);
        showToast("Error: " + err.message, "error");
    }
}

async function logout() {
    await fetch(`${API_URL}/api/logout`, { method: 'POST', credentials: 'include' });
    showLoginModal();
}

// Show login modal - require manual login
function showLoginModal() {
    document.getElementById('auth-modal').classList.add('active');
    document.getElementById('app-layout').classList.remove('visible');
    // Clear any previous session display
    document.getElementById('current-agent').textContent = 'Unknown';
    document.getElementById('current-role').textContent = 'Guest';
}

// --- TAB NAVIGATION ---
document.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', (e) => {
        document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        
        const targetId = e.currentTarget.getAttribute('data-tab');
        e.currentTarget.classList.add('active');
        document.getElementById(targetId).classList.add('active');
        
        if (targetId === 'tab-database') fetchStatus();
        if (targetId === 'tab-admin') loadAdminSuspects();
        if (targetId === 'tab-canvas') {
            if(fabricCanvas) fabricCanvas.renderAll();
        }
    });
});

// --- FABRIC JS INTERACTIVE CANVAS ---
function initCanvas() {
    fabricCanvas = new fabric.Canvas('fabricCanvas', { backgroundColor: '#ffffff', preserveObjectStacking: true });
    loadCategoryAssets();
}

async function loadCategoryAssets() {
    const category = document.getElementById('asset-category').value;
    const grid = document.getElementById('asset-grid');
    if(!grid) return;
    
    // Add loading indicator
    grid.innerHTML = '<div class="loader" style="margin:2rem auto;"></div>';
    
    try {
        const response = await fetch(`${API_URL}/api/assets/${category}`);
        const files = await response.json();
        
        grid.innerHTML = '';
        if(files.length === 0) {
            grid.innerHTML = '<p style="font-size:0.8rem; color:#bbb;">No designs found.</p>';
            return;
        }
        
        files.forEach(file => {
            const url = `${API_URL}/static/assets/${category}/${file}`;
            const img = document.createElement('img');
            img.src = url;
            img.style.width = '100%';
            img.style.cursor = 'pointer';
            img.style.background = 'rgba(255,255,255,0.9)';
            img.style.borderRadius = '8px';
            img.style.padding = '8px';
            img.style.border = '2px solid transparent';
            img.onload = () => { grid.appendChild(img); };
            img.onmouseover = () => img.style.borderColor = '#8b5cf6';
            img.onmouseout = () => img.style.borderColor = 'transparent';
            img.onclick = () => addAssetToCanvas(url);
        });
    } catch(err) {
        grid.innerHTML = '<p style="color:#ef4444; font-size:0.8rem;">Failed to load assets</p>';
    }
}

function addAssetToCanvas(url) {
    if(!fabricCanvas) return;
    
    // Standardize object options for uniform bounding boxes
    const objOptions = {
        left: 250, top: 250, originX: 'center', originY: 'center',
        transparentCorners: false, cornerColor: '#8b5cf6',
        cornerStrokeColor: '#ffffff', borderColor: '#8b5cf6',
        cornerSize: 10, padding: 5
    };

    if(url.toLowerCase().endsWith('.svg')) {
        fabric.loadSVGFromURL(url, function(objects, options) {
            const obj = fabric.util.groupSVGElements(objects, options);
            obj.set(objOptions);
            fabricCanvas.add(obj);
            fabricCanvas.setActiveObject(obj);
            fabricCanvas.renderAll();
        });
    } else {
        // Load JPG, PNG original designs into the canvas
        fabric.Image.fromURL(url, function(img) {
            img.set(objOptions);
            
            // Automatically scale down large images if necessary
            if (img.width > 200) {
                img.scaleToWidth(200);
            }
            
            fabricCanvas.add(img);
            fabricCanvas.setActiveObject(img);
            fabricCanvas.renderAll();
        // CORS config for generic imaging
        }, { crossOrigin: 'anonymous' });
    }
}

function uploadToCanvas(e) {
    if (!fabricCanvas) return;
    const file = e.target.files[0];
    if (!file) return;
    if (!file.type.match('image.*')) { showToast('Images only.', 'error'); return; }

    const reader = new FileReader();
    reader.onload = function(evt) {
        fabric.Image.fromURL(evt.target.result, function(img) {
            const objOptions = {
                left: 250, top: 250, originX: 'center', originY: 'center',
                transparentCorners: false, cornerColor: '#8b5cf6',
                cornerStrokeColor: '#ffffff', borderColor: '#8b5cf6',
                cornerSize: 10, padding: 5
            };
            img.set(objOptions);
            
            if (img.width > 200) {
                img.scaleToWidth(200);
            }
            
            fabricCanvas.add(img);
            fabricCanvas.setActiveObject(img);
            fabricCanvas.renderAll();
        });
    };
    reader.readAsDataURL(file);
    e.target.value = ''; // Reset for consecutive uploads
}

function bringForward() {
    const obj = fabricCanvas.getActiveObject();
    if(obj) { fabricCanvas.bringForward(obj); fabricCanvas.renderAll(); }
}

function sendBackward() {
    const obj = fabricCanvas.getActiveObject();
    if(obj) { fabricCanvas.sendBackward(obj); fabricCanvas.renderAll(); }
}

function deleteSelected() {
    const obj = fabricCanvas.getActiveObject();
    if(obj) { fabricCanvas.remove(obj); }
}

function clearCanvas() {
    if(fabricCanvas) {
        fabricCanvas.clear();
        fabricCanvas.backgroundColor = '#ffffff';
        fabricCanvas.renderAll();
    }
}

// --- DRAG DROP & PREVIEW ---
function handleDrop(e, inputId) {
    e.preventDefault();
    const files = e.dataTransfer.files;
    if(files.length > 0) {
        document.getElementById(inputId).files = files;
        const targetPreview = inputId === 'gen-input' ? 'gen-preview' : 'rec-preview';
        if(inputId !== 'admin-s-file') handleFileSelect({target: document.getElementById(inputId)}, targetPreview);
        else document.getElementById('admin-file-name').textContent = files[0].name;
    }
    e.currentTarget.classList.remove('dragover');
}
document.querySelectorAll('.upload-area').forEach(a => {
    a.addEventListener('dragover', e => { e.preventDefault(); a.classList.add('dragover'); });
    a.addEventListener('dragleave', e => { e.preventDefault(); a.classList.remove('dragover'); });
});

function handleFileSelect(e, previewId) {
    const file = e.target.files[0];
    if (!file) return;
    if (!file.type.match('image.*')) { showToast('Images only.', 'error'); return; }

    const reader = new FileReader();
    reader.onload = function(evt) {
        if (previewId === 'gen-preview') {
            generateFile = file;
            document.getElementById('gen-img-preview').src = evt.target.result;
            document.getElementById('gen-preview').classList.remove('hidden');
            document.getElementById('gen-results').classList.add('hidden');
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

// --- MAIN AI ACTIONS ---
async function generateSketch() {
    if (!generateFile) { showToast("Select image", "error"); return; }

    document.querySelector('#gen-preview .btn-text').style.display = 'none';
    document.getElementById('gen-loader').classList.remove('hidden');

    const fd = new FormData(); fd.append('file', generateFile);
    try {
        const r = await fetch(`${API_URL}/api/generate-sketch`, { method: 'POST', body: fd, credentials: 'include' });
        const res = await r.json();
        
        if(res.success) {
            document.getElementById('gen-preview').classList.add('hidden');
            document.getElementById('gen-results').classList.remove('hidden');
            const ts = Date.now();
            document.getElementById('gen-res-orig').src = `${API_URL}${res.original_url}?t=${ts}`;
            document.getElementById('gen-res-sketch').src = `${API_URL}${res.sketch_url}?t=${ts}`;
            showToast("Sketch Generator Active", "success");
            setTimeout(() => {
                document.getElementById('upload-gen').style.display = 'block';
                generateFile = null;
            }, 6000);
        } else { throw new Error(res.error); }
    } catch(err) { showToast(err.message, "error"); }
    
    document.querySelector('#gen-preview .btn-text').style.display = 'block';
    document.getElementById('gen-loader').classList.add('hidden');
}

async function recognizeFromCanvas() {
    if(!fabricCanvas) return;
    document.querySelector('#canvas-loader').classList.remove('hidden');
    
    // Switch to recognition tab visually
    document.querySelector('[data-tab="tab-recognize"]').click();
    
    const dataURL = fabricCanvas.toDataURL({ format: 'png', quality: 1.0 });
    
    const fd = new FormData();
    fd.append('base64_image', dataURL);
    await executeMatch(fd);
    document.querySelector('#canvas-loader').classList.add('hidden');
}

async function recognizeSuspect() {
    if (!recognizeFile) return;
    document.querySelector('#rec-preview .btn-text').style.display = 'none';
    document.getElementById('rec-loader').classList.remove('hidden');
    
    const fd = new FormData(); fd.append('file', recognizeFile);
    await executeMatch(fd);
    
    document.querySelector('#rec-preview .btn-text').style.display = 'block';
    document.getElementById('rec-loader').classList.add('hidden');
}

async function executeMatch(formData) {
    try {
        const r = await fetch(`${API_URL}/api/recognize-sketch`, { method: 'POST', body: formData, credentials: 'include' });
        const res = await r.json();
        
        if(res.success) {
            document.getElementById('rec-preview').classList.add('hidden');
            document.getElementById('upload-rec').style.display = 'none';
            document.getElementById('rec-results').classList.remove('hidden');
            
            const ts = Date.now();
            document.getElementById('rec-res-query').src = `${API_URL}${res.query_url}?t=${ts}`;
            document.getElementById('rec-res-match').src = res.match_url ? `${API_URL}${res.match_url}?t=${ts}` : 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect width="10" height="10" fill="gray"/></svg>';
            
            document.getElementById('rec-match-name').textContent = res.match_name.replace(/_/g, " ").toUpperCase();
            document.getElementById('rec-match-desc').textContent = res.description || '';
            document.getElementById('rec-confidence').textContent = `${res.confidence}%`;
            document.getElementById('rec-confidence').style.color = res.confidence > 80 ? '#10b981' : (res.confidence > 50 ? '#eab308' : '#ef4444');
            
            showToast("Match Engine Complete", "success");
            setTimeout(() => {
                document.getElementById('upload-rec').style.display = 'block';
                recognizeFile = null;
            }, 8000);
        } else { throw new Error(res.error); }
    } catch(err) { showToast(err.message, "error"); }
}

// --- ADMIN / DB FUNCTIONS ---
async function fetchStatus() {
    try {
        const r = await fetch(`${API_URL}/api/status`);
        const res = await r.json();
        document.getElementById('stat-db-size').textContent = res.database_size;
        const el = document.getElementById('stat-trained');
        el.textContent = res.is_trained ? "Yes" : "No";
        el.style.color = res.is_trained ? "#10b981" : "#ef4444";
    } catch(err) {}
}

async function loadAdminSuspects() {
    try {
        const r = await fetch(`${API_URL}/api/admin/suspects`, { credentials: 'include' });
        const suspects = await r.json();
        const list = document.getElementById('suspects-list');
        list.innerHTML = '';
        suspects.forEach(s => {
            list.innerHTML += `<div class="suspect-item">
                <img src="${API_URL}/database/${s.filename}" onerror="this.src=''">
                <div class="suspect-details">
                    <h4>${s.name.replace(/_/g, " ").toUpperCase()}</h4>
                    <p>${s.description ? s.description.substring(0,40)+'...' : 'No record'}</p>
                </div>
            </div>`;
        });
    } catch(err) { console.error("Admin Load Failed"); }
}

async function uploadSuspectAdmin() {
    const file = document.getElementById('admin-s-file').files[0];
    const name = document.getElementById('admin-s-name').value;
    const desc = document.getElementById('admin-s-desc').value;
    
    if(!file || !name) { showToast("Name and Photo required", "error"); return; }
    
    const fd = new FormData();
    fd.append('file', file);
    fd.append('name', name);
    fd.append('description', desc);
    
    try {
        const r = await fetch(`${API_URL}/api/admin/suspects`, { method: 'POST', body: fd, credentials: 'include' });
        const res = await r.json();
        if(res.success) {
            showToast("Suspect Added. AI Model Retrained.", "success");
            document.getElementById('admin-s-name').value = '';
            document.getElementById('admin-s-desc').value = '';
            document.getElementById('admin-file-name').textContent = '';
            document.getElementById('admin-s-file').value = '';
            loadAdminSuspects();
        }
    } catch(err) { showToast("Upload Failed", "error"); }
}

function showToast(msg, type='info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`; toast.textContent = msg;
    container.appendChild(toast);
    setTimeout(() => { if(toast.parentElement) toast.remove(); }, 5000);
}
