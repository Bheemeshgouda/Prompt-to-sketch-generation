import os
import threading
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash

from image_generator import generate_sketch_image, load_model  # your existing module

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'

# MySQL Config — adjust as needed:
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'criminal_composite_db'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

# Upload folder for images
UPLOAD_FOLDER = os.path.join('static', 'generated')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Load model once on startup
try:
    load_model()
except Exception as e:
    print(f"[ERROR] Failed to preload AI model: {e}")

# Thread lock for sketch generation (GPU concurrency safety)
generation_lock = threading.Lock()

# --- Helper decorators ---

@app.context_processor
def inject_now():
    return {'now': datetime.now()}


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session.get('role') != role:
                flash('Permission denied.', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated
    return decorator

# --- Background sketch generation thread ---

class SketchGenerator(threading.Thread):
    def __init__(self, prompt, save_path, case_id, user_id, description):
        super().__init__()
        self.prompt = prompt
        self.save_path = save_path
        self.case_id = case_id
        self.user_id = user_id
        self.description = description

    def run(self):
        with generation_lock:
            try:
                ret_path = generate_sketch_image(self.prompt, self.save_path)
                if not ret_path:
                    print("[ERROR] Sketch generation failed.")
                    return

                with app.app_context():
                    cur = mysql.connection.cursor()
                    cur.execute(
                        """
                        INSERT INTO composites (case_id, user_id, description, image_path)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (self.case_id, self.user_id, self.description, os.path.basename(self.save_path))
                    )
                    mysql.connection.commit()
                    cur.close()
                print(f"[INFO] Sketch generated and saved to DB: {self.save_path}")
            except Exception as e:
                print(f"[ERROR] SketchGenerator thread error: {e}")

# --- Routes ---

@app.route('/')
@login_required
def index():
    try:
        cur = mysql.connection.cursor()
        if session['role'] == 'admin':
            # Admin sees all recent cases:
            cur.execute("SELECT c.*, u.full_name FROM cases c JOIN users u ON c.created_by = u.id ORDER BY c.created_at DESC LIMIT 5")
        else:
            # Officers see only their created cases
            cur.execute("""
                SELECT c.*, u.full_name
                FROM cases c JOIN users u ON c.created_by = u.id
                WHERE c.created_by = %s
                ORDER BY c.created_at DESC LIMIT 5
            """, (session['user_id'],))
        recent_cases = cur.fetchall()
        cur.close()
        return render_template('index.html', recent_cases=recent_cases)
    except Exception as e:
        flash(f"Database error: {e}", "danger")
        return redirect(url_for('logout'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('login'))

        cur = mysql.connection.cursor()
        # Allow login via username or badge number
        cur.execute("SELECT * FROM users WHERE username = %s OR badge_number = %s", (username, username))
        user = cur.fetchone()
        cur.close()

        if user and check_password_hash(user['password'], password):
            session['logged_in'] = True
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['full_name'] = user['full_name']
            session['badge_number'] = user['badge_number']
            session['role'] = user['role']
            flash('Login successful.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials.', 'danger')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        full_name = request.form.get('full_name', '').strip()
        badge_number = request.form.get('badge_number', '').strip()
        role = request.form.get('role', 'officer').strip()

        if not all([username, password, full_name, badge_number]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('register'))

        try:
            cur = mysql.connection.cursor()
            # Check username uniqueness
            cur.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cur.fetchone():
                flash('Username already exists.', 'warning')
                cur.close()
                return redirect(url_for('register'))

            hashed_password = generate_password_hash(password)
            cur.execute(
                "INSERT INTO users (username, password, full_name, badge_number, role) VALUES (%s, %s, %s, %s, %s)",
                (username, hashed_password, full_name, badge_number, role)
            )
            mysql.connection.commit()
            cur.close()
            flash('User registered successfully.', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'Error: {e}', 'danger')
            mysql.connection.rollback()
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/cases')
@login_required
def cases():
    search_query = request.args.get('search', '').strip()
    try:
        cur = mysql.connection.cursor()
        if session['role'] == 'admin':
            if search_query:
                like_pattern = f"%{search_query}%"
                cur.execute("""
                    SELECT c.*, u.full_name
                    FROM cases c JOIN users u ON c.created_by = u.id
                    WHERE c.case_number LIKE %s OR c.description LIKE %s OR c.location LIKE %s
                    ORDER BY c.created_at DESC
                """, (like_pattern, like_pattern, like_pattern))
            else:
                cur.execute("SELECT c.*, u.full_name FROM cases c JOIN users u ON c.created_by = u.id ORDER BY c.created_at DESC")
        else:
            if search_query:
                like_pattern = f"%{search_query}%"
                cur.execute("""
                    SELECT c.*, u.full_name
                    FROM cases c JOIN users u ON c.created_by = u.id
                    WHERE c.created_by = %s AND (c.case_number LIKE %s OR c.description LIKE %s OR c.location LIKE %s)
                    ORDER BY c.created_at DESC
                """, (session['user_id'], like_pattern, like_pattern, like_pattern))
            else:
                cur.execute("""
                    SELECT c.*, u.full_name
                    FROM cases c JOIN users u ON c.created_by = u.id
                    WHERE c.created_by = %s
                    ORDER BY c.created_at DESC
                """, (session['user_id'],))
        cases_list = cur.fetchall()
        cur.close()
        return render_template('cases.html', cases=cases_list)
    except Exception as e:
        flash(f"Database error: {e}", "danger")
        return redirect(url_for('index'))

@app.route('/create-case', methods=['GET', 'POST'])
@login_required
def create_case():
    if request.method == 'POST':
        case_number = request.form.get('case_number', '').strip()
        description = request.form.get('description', '').strip()
        location = request.form.get('location', '').strip()
        incident_date = request.form.get('incident_date')

        if not all([case_number, description, location, incident_date]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('create_case'))

        try:
            cur = mysql.connection.cursor()
            cur.execute(
                "INSERT INTO cases (case_number, description, location, incident_date, created_by) VALUES (%s, %s, %s, %s, %s)",
                (case_number, description, location, incident_date, session['user_id'])
            )
            mysql.connection.commit()
            case_id = cur.lastrowid
            cur.close()
            flash('Case created successfully.', 'success')
            return redirect(url_for('create_composite', case_id=case_id))
        except Exception as e:
            mysql.connection.rollback()
            flash(f"Error creating case: {e}", "danger")
            return redirect(url_for('create_case'))

    return render_template('create_case.html')

@app.route('/case/<int:case_id>')
@login_required
def view_case(case_id):
    try:
        cur = mysql.connection.cursor()
        # Fetch case + creator info
        cur.execute("""
            SELECT c.*, u.full_name
            FROM cases c JOIN users u ON c.created_by = u.id
            WHERE c.id = %s
        """, (case_id,))
        case = cur.fetchone()

        if not case:
            cur.close()
            flash('Case not found.', 'danger')
            return redirect(url_for('index'))

        # Fetch composites + author info
        cur.execute("""
            SELECT co.*, u.full_name
            FROM composites co JOIN users u ON co.user_id = u.id
            WHERE co.case_id = %s
            ORDER BY co.created_at DESC
        """, (case_id,))
        composites = cur.fetchall()

        cur.close()
        return render_template('view_case.html', case=case, composites=composites)
    except Exception as e:
        flash(f"Database error: {e}", "danger")
        return redirect(url_for('index'))

@app.route('/create-composite/<int:case_id>', methods=['GET', 'POST'])
@login_required
def create_composite(case_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM cases WHERE id = %s", (case_id,))
    case = cur.fetchone()
    if not case:
        cur.close()
        flash('Case not found.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        description = request.form.get('description', '').strip()
        if not description:
            flash('Suspect description is required.', 'danger')
            cur.close()
            return redirect(url_for('create_composite', case_id=case_id))

        full_prompt = (
            f"Police sketch of a criminal with features: {description}. "
            "Forensic sketch, black and white, front view, clean lines, high detail."
        )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sketch_{case_id}_{timestamp}.png"
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        # Launch background thread for image generation
        SketchGenerator(full_prompt, save_path, case_id, session['user_id'], full_prompt).start()

        flash("Sketch generation started. Please check back soon.", 'info')
        cur.close()
        return redirect(url_for('view_case', case_id=case_id))

    cur.close()
    return render_template('create_composite.html', case=case)

@app.route('/composite/<int:composite_id>', methods=['GET', 'POST'])
@login_required
def view_composite(composite_id):
    cur = mysql.connection.cursor()
    # Fetch composite + user info
    cur.execute("""
        SELECT co.*, u.full_name, u.badge_number
        FROM composites co JOIN users u ON co.user_id = u.id
        WHERE co.id = %s
    """, (composite_id,))
    composite = cur.fetchone()

    if not composite:
        cur.close()
        flash('Composite not found.', 'danger')
        return redirect(url_for('index'))

    # Fetch revisions + requester info (assuming revisions has user_id column)
    cur.execute("""
        SELECT r.*, u.full_name
        FROM revisions r LEFT JOIN users u ON r.user_id = u.id
        WHERE r.composite_id = %s
        ORDER BY r.created_at DESC
    """, (composite_id,))
    revisions = cur.fetchall()

    # Handle POST form submissions
    if request.method == 'POST':
        if 'accurate' in request.form:
            try:
                cur.execute("UPDATE composites SET is_accurate = 1 WHERE id = %s", (composite_id,))
                mysql.connection.commit()
                flash('Composite marked as accurate.', 'success')
            except Exception as e:
                flash(f'Error updating composite: {e}', 'danger')
            return redirect(url_for('view_composite', composite_id=composite_id))

        elif 'adjustment_details' in request.form:
            adjustment_text = request.form.get('adjustment_details', '').strip()
            if not adjustment_text:
                flash('Adjustment details are required.', 'danger')
                return redirect(url_for('view_composite', composite_id=composite_id))

            # Here you would start a background process to generate the revised sketch,
            # then insert a revision row after generation.
            # This is a placeholder for your implementation.

            flash('Revision request submitted, sketch generation should start shortly.', 'info')
            return redirect(url_for('view_composite', composite_id=composite_id))

    cur.close()
    return render_template('composite.html', composite=composite, revisions=revisions)

if __name__ == '__main__':
    app.run(debug=True, threaded=True)
