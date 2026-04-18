from flask import Flask, request, jsonify, render_template, send_from_directory, session
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from ml_core import ForensicMLSystem
from flask_sqlalchemy import SQLAlchemy
import base64
import uuid

# ── New services ───────────────────────────────────────────────────────────────
from services.sketch_service  import generate_composite
from services.enhance_service import enhance_sketch
from services.matcher_service import FaceMatcher

app = Flask(__name__, static_folder="static", template_folder=".")
app.config['SECRET_KEY'] = 'thirdeye_secret_key_123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///thirdeye.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

@app.after_request
def after_request(response):
    origin = request.headers.get('Origin')
    if origin:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    return response

CORS(app, supports_credentials=True)

UPLOAD_FOLDER   = 'uploads'
DATABASE_FOLDER = 'database'
os.makedirs(UPLOAD_FOLDER,   exist_ok=True)
os.makedirs(DATABASE_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER']    = UPLOAD_FOLDER
app.config['DATABASE_FOLDER']  = DATABASE_FOLDER

db = SQLAlchemy(app)

# ── Database Models ────────────────────────────────────────────────────────────
class User(db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80),  unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role     = db.Column(db.String(20),  default='user')

class SuspectDB(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(100), nullable=False)
    filename    = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)

# ── AI Systems ─────────────────────────────────────────────────────────────────
ml_system   = ForensicMLSystem(DATABASE_FOLDER)     # photo → pencil sketch
face_matcher = FaceMatcher(DATABASE_FOLDER)          # HOG cosine-similarity matcher

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_admin():
    return session.get('role') == 'admin'

# ── Static routes ──────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/database/<filename>')
def serve_database_file(filename):
    return send_from_directory(DATABASE_FOLDER, filename)

@app.route('/uploads/<filename>')
def serve_upload_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# ── Authentication ─────────────────────────────────────────────────────────────
@app.route('/api/register', methods=['POST'])
def register():
    data     = request.json
    username = data.get('username')
    password = data.get('password')
    role     = data.get('role', 'user')

    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 400

    hashed_pw = generate_password_hash(password)
    new_user  = User(username=username, password=hashed_pw, role=role)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Registration successful'})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data.get('username')).first()
    if user and check_password_hash(user.password, data.get('password')):
        session['user_id']  = user.id
        session['username'] = user.username
        session['role']     = user.role
        return jsonify({'success': True, 'role': user.role, 'username': user.username})
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/me', methods=['GET'])
def get_me():
    if 'user_id' in session:
        return jsonify({'logged_in': True, 'username': session['username'], 'role': session['role']})
    return jsonify({'logged_in': False})

# ── Pipeline 1 — Photo → Pencil Sketch ────────────────────────────────────────
@app.route('/api/generate-sketch', methods=['POST'])
def api_generate_sketch():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file and allowed_file(file.filename):
        filename        = secure_filename(file.filename)
        input_path      = os.path.join(UPLOAD_FOLDER, filename)
        sketch_filename = "sketch_" + filename
        output_path     = os.path.join(UPLOAD_FOLDER, sketch_filename)
        file.save(input_path)

        sketch = ml_system.generate_sketch(input_path, save_path=output_path)
        if sketch is None:
            return jsonify({'error': 'Could not process image'}), 500

        return jsonify({
            'success':      True,
            'original_url': f'/uploads/{filename}',
            'sketch_url':   f'/uploads/{sketch_filename}'
        })
    return jsonify({'error': 'Invalid file'}), 400

# ── Pipeline 1b — Eyewitness Description → Forensic Composite Sketch ──────────
@app.route('/api/describe-sketch', methods=['POST'])
def api_describe_sketch():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    attrs = request.json or {}

    filename = f"composite_{uuid.uuid4().hex}.png"
    save_path = os.path.join(UPLOAD_FOLDER, filename)

    try:
        generate_composite(attrs, save_path=save_path)
    except Exception as e:
        return jsonify({'error': f'Sketch generation failed: {str(e)}'}), 500

    return jsonify({
        'success':     True,
        'sketch_url':  f'/uploads/{filename}',
        'filename':    filename
    })

# ── Pipeline 2 — Sketch → Enhanced Photorealistic ─────────────────────────────
@app.route('/api/enhance-sketch', methods=['POST'])
def api_enhance_sketch():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    # Accept either uploaded file or a filename reference already on server
    if 'file' in request.files:
        file = request.files['file']
        if not file or not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file'}), 400
        filename  = secure_filename(file.filename)
        src_path  = os.path.join(UPLOAD_FOLDER, filename)
        file.save(src_path)
    elif 'filename' in request.form:
        src_path = os.path.join(UPLOAD_FOLDER, secure_filename(request.form['filename']))
        if not os.path.exists(src_path):
            return jsonify({'error': 'File not found on server'}), 404
    else:
        return jsonify({'error': 'No image provided'}), 400

    enhanced_filename = "enhanced_" + os.path.basename(src_path)
    enhanced_path     = os.path.join(UPLOAD_FOLDER, enhanced_filename)

    try:
        enhance_sketch(src_path, save_path=enhanced_path)
    except Exception as e:
        return jsonify({'error': f'Enhancement failed: {str(e)}'}), 500

    return jsonify({
        'success':      True,
        'enhanced_url': f'/uploads/{enhanced_filename}'
    })

# ── Pipeline 3 — Sketch / Photo Suspect Matching ──────────────────────────────
@app.route('/api/recognize-sketch', methods=['POST'])
def api_recognize():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    if 'base64_image' in request.form:
        image_data = request.form['base64_image'].split(',')[-1]
        filename   = f"query_{uuid.uuid4().hex}.png"
        input_path = os.path.join(UPLOAD_FOLDER, filename)
        with open(input_path, "wb") as fh:
            fh.write(base64.b64decode(image_data))

    elif 'file' in request.files:
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename   = "query_" + secure_filename(file.filename)
            input_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(input_path)
        else:
            return jsonify({'error': 'Invalid file'}), 400
    else:
        return jsonify({'error': 'No image provided'}), 400

    # ── HOG cosine-similarity matching ────────────────────────────────────
    result = face_matcher.match(input_path, top_k=5)

    if not result.get('success'):
        return jsonify({'success': False, 'error': result.get('error', 'Matching failed')}), 500

    # Enrich matches with DB descriptions
    for m in result['matches']:
        db_rec = SuspectDB.query.filter_by(name=m['name']).first()
        m['description'] = db_rec.description if db_rec else 'No additional records on file.'

    best_name = result['best_match']
    db_best   = SuspectDB.query.filter_by(name=best_name).first()

    return jsonify({
        'success':     True,
        'matches':     result['matches'],            # top-5 ranked list
        'match_name':  best_name,
        'confidence':  result['best_score'],
        'tier':        result['best_tier'],
        'query_url':   f'/uploads/{filename}',
        'match_url':   f'/database/{result["best_image"]}' if result['best_image'] else None,
        'description': db_best.description if db_best else 'No records on file.'
    })

# ── Asset serving ──────────────────────────────────────────────────────────────
@app.route('/api/assets/<category>', methods=['GET'])
def get_assets(category):
    category_path = os.path.join(app.static_folder, 'assets', category)
    if not os.path.exists(category_path):
        return jsonify([])
    files = [f for f in os.listdir(category_path) if f.endswith(('.png', '.jpg', '.jpeg', '.svg'))]
    return jsonify(files)

# ── Admin ──────────────────────────────────────────────────────────────────────
@app.route('/api/admin/suspects', methods=['GET', 'POST'])
def handle_suspects():
    if not is_admin():
        return jsonify({'error': 'Admin access required'}), 403

    if request.method == 'GET':
        suspects = SuspectDB.query.all()
        return jsonify([{'id': s.id, 'name': s.name, 'filename': s.filename,
                         'description': s.description} for s in suspects])

    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'error': 'No file'}), 400
        file = request.files['file']
        name = request.form.get('name')
        desc = request.form.get('description', '')

        if file and allowed_file(file.filename) and name:
            ext       = file.filename.rsplit('.', 1)[1].lower()
            safe_name = name.replace(" ", "_")
            filename  = f"{safe_name}.{ext}"
            filepath  = os.path.join(DATABASE_FOLDER, filename)
            file.save(filepath)

            # Rebuild HOG index + legacy PCA
            face_matcher.build_index()
            ml_system.prepare_data()

            new_s = SuspectDB(name=safe_name, filename=filename, description=desc)
            db.session.add(new_s)
            db.session.commit()
            return jsonify({'success': True})

    return jsonify({'error': 'Invalid request'}), 400

@app.route('/api/admin/suspects/<int:suspect_id>', methods=['DELETE'])
def delete_suspect(suspect_id):
    if not is_admin():
        return jsonify({'error': 'Admin access required'}), 403

    suspect = SuspectDB.query.get(suspect_id)
    if not suspect:
        return jsonify({'error': 'Not found'}), 404

    # Remove file from disk
    filepath = os.path.join(DATABASE_FOLDER, suspect.filename)
    if os.path.exists(filepath):
        os.remove(filepath)

    db.session.delete(suspect)
    db.session.commit()
    face_matcher.build_index()  # Rebuild index
    return jsonify({'success': True})

@app.route('/api/status', methods=['GET'])
def api_status():
    files   = [f for f in os.listdir(DATABASE_FOLDER) if f.endswith(('.png', '.jpg', '.jpeg'))]
    trained = face_matcher.is_trained
    return jsonify({
        'database_size': len(files),
        'is_trained':    trained,
        'status':        'Online'
    })

# ── DB init ────────────────────────────────────────────────────────────────────
def initialize_db():
    with app.app_context():
        db.create_all()

        if not User.query.filter_by(username='admin').first():
            hashed_pw = generate_password_hash('admin123')
            admin     = User(username='admin', password=hashed_pw, role='admin')
            db.session.add(admin)

        existing_files = [f for f in os.listdir(DATABASE_FOLDER) if allowed_file(f)]
        for f in existing_files:
            name = os.path.splitext(f)[0]
            if not SuspectDB.query.filter_by(name=name).first():
                s = SuspectDB(name=name, filename=f, description="Migrated from file system.")
                db.session.add(s)

        db.session.commit()

        # Build HOG index
        try:
            face_matcher.build_index()
            print(f"HOG index built: {len(face_matcher.index)} embeddings.")
        except Exception as e:
            print(f"HOG index build failed: {e}")

        # Legacy PCA train
        try:
            ml_system.prepare_data()
        except Exception as e:
            print(f"PCA train skipped: {e}")

# ── Entry point ────────────────────────────────────────────────────────────────
import webbrowser
from waitress import serve
import sys
import threading
import time

def open_browser():
    time.sleep(1.5)
    webbrowser.open('http://localhost:5000/')

if __name__ == '__main__':
    sys.stdout.reconfigure(line_buffering=True)

    print("=" * 50)
    print("  Third Eye - AI Forensic System")
    print("=" * 50)
    print()
    print("Initializing database...")
    initialize_db()
    print("Database ready!")
    print()
    print("Starting server at http://localhost:5000/ ...")
    print("-" * 50)

    threading.Thread(target=open_browser, daemon=True).start()
    serve(app, host="127.0.0.1", port=5000)
