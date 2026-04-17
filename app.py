from flask import Flask, request, jsonify, render_template, send_from_directory, session
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from ml_core import ForensicMLSystem
from flask_sqlalchemy import SQLAlchemy
import base64
import uuid

app = Flask(__name__, static_folder="static", template_folder=".")
app.config['SECRET_KEY'] = 'thirdeye_secret_key_123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///thirdeye.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
CORS(app, supports_credentials=True, origins=["http://127.0.0.1", "http://localhost", "http://127.0.0.1:5000", "http://localhost:5000"])

UPLOAD_FOLDER = 'uploads'
DATABASE_FOLDER = 'database'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DATABASE_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='user')

class SuspectDB(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    filename = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)

# Initialize Machine Learning System
ml_system = ForensicMLSystem(DATABASE_FOLDER)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_admin():
    return session.get('role') == 'admin'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/database/<filename>')
def serve_database_file(filename):
    return send_from_directory(DATABASE_FOLDER, filename)

@app.route('/uploads/<filename>')
def serve_upload_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# --- AUTHENTICATION ROUTES ---
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'user') # default is user, maybe admin for demo
    
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 400
        
    hashed_pw = generate_password_hash(password)
    new_user = User(username=username, password=hashed_pw, role=role)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Registration successful'})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data.get('username')).first()
    if user and check_password_hash(user.password, data.get('password')):
        session['user_id'] = user.id
        session['username'] = user.username
        session['role'] = user.role
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

# --- ML & SKETCH ROUTES ---
@app.route('/api/generate-sketch', methods=['POST'])
def api_generate_sketch():
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
    
    if 'file' not in request.files: return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(input_path)
        
        sketch_filename = "sketch_" + filename
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], sketch_filename)
        
        sketch = ml_system.generate_sketch(input_path, save_path=output_path)
        if sketch is None: return jsonify({'error': 'Could not process image'}), 500
        return jsonify({'success': True, 'original_url': f'/uploads/{filename}', 'sketch_url': f'/uploads/{sketch_filename}'})
    return jsonify({'error': 'Invalid file'}), 400

@app.route('/api/recognize-sketch', methods=['POST'])
def api_recognize():
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
    
    # Check if a base64 encoded string is sent (from interactive sketch)
    if 'base64_image' in request.form:
        image_data = request.form['base64_image']
        # remove header "data:image/png;base64,"
        image_data = image_data.split(',')[1]
        filename = f"query_{uuid.uuid4().hex}.png"
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        with open(input_path, "wb") as fh:
            fh.write(base64.b64decode(image_data))
    elif 'file' in request.files:
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            input_path = os.path.join(app.config['UPLOAD_FOLDER'], "query_" + filename)
            file.save(input_path)
        else:
            return jsonify({'error': 'Invalid file'}), 400
    else:
        return jsonify({'error': 'No image provided'}), 400
        
    result = ml_system.recognize(input_path)
    if "error" in result: return jsonify({'success': False, 'error': result["error"]}), 500
    
    db_match = SuspectDB.query.filter_by(name=result['match']).first()
    description = db_match.description if db_match else "No additional records on file."
        
    return jsonify({
        'success': True,
        'match_name': result['match'],
        'confidence': result['confidence'],
        'query_url': f'/uploads/{filename}',
        'match_url': f'/database/{result["match_image"]}' if result["match_image"] else None,
        'description': description
    })

@app.route('/api/assets/<category>', methods=['GET'])
def get_assets(category):
    category_path = os.path.join(app.static_folder, 'assets', category)
    if not os.path.exists(category_path):
        return jsonify([])
    files = [f for f in os.listdir(category_path) if f.endswith(('.png', '.jpg', '.jpeg', '.svg'))]
    return jsonify(files)


# --- ADMIN ROUTES ---
@app.route('/api/admin/suspects', methods=['GET', 'POST'])
def handle_suspects():
    if not is_admin(): return jsonify({'error': 'Admin access required'}), 403
    
    if request.method == 'GET':
        suspects = SuspectDB.query.all()
        return jsonify([{'id': s.id, 'name': s.name, 'filename': s.filename, 'description': s.description} for s in suspects])
        
    if request.method == 'POST':
        if 'file' not in request.files: return jsonify({'error': 'No file'}), 400
        file = request.files['file']
        name = request.form.get('name')
        desc = request.form.get('description', '')
        
        if file and allowed_file(file.filename) and name:
            ext = file.filename.rsplit('.', 1)[1].lower()
            safe_name = name.replace(" ", "_")
            filename = f"{safe_name}.{ext}"
            filepath = os.path.join(app.config['DATABASE_FOLDER'], filename)
            file.save(filepath)
            
            # Retrain Model
            ml_system.prepare_data()
            
            new_s = SuspectDB(name=safe_name, filename=filename, description=desc)
            db.session.add(new_s)
            db.session.commit()
            return jsonify({'success': True})
            
    return jsonify({'error': 'Invalid request'}), 400

@app.route('/api/status', methods=['GET'])
def api_status():
    files = [f for f in os.listdir(DATABASE_FOLDER) if f.endswith(('.png', '.jpg', '.jpeg'))]
    trained = ml_system.is_trained
    return jsonify({
        'database_size': len(files),
        'is_trained': trained,
        'status': 'Online'
    })

def initialize_db():
    with app.app_context():
        db.create_all()
        # Create default admin if not exists
        if not User.query.filter_by(username='admin').first():
            hashed_pw = generate_password_hash('admin123')
            admin = User(username='admin', password=hashed_pw, role='admin')
            db.session.add(admin)
            
        # Migrate existing files in database folder to SQLite
        existing_files = [f for f in os.listdir(DATABASE_FOLDER) if allowed_file(f)]
        for f in existing_files:
            name = os.path.splitext(f)[0]
            if not SuspectDB.query.filter_by(name=name).first():
                s = SuspectDB(name=name, filename=f, description="Migrated from file system.")
                db.session.add(s)
        db.session.commit()
        
        # Train ML
        try:
            ml_system.prepare_data()
        except Exception as e:
            print(f"Initial ML train failed: {e}")

if __name__ == '__main__':
    initialize_db()
    app.run(debug=True, port=5000)
