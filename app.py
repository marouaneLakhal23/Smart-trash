# Import necessary libraries
from flask import Flask, jsonify, request, redirect, url_for, session, render_template_string, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import secrets
from functools import wraps # Import wraps

# Initialize Flask app
app = Flask(__name__, static_folder='static', static_url_path='/static') # Ensure static folder is configured

# Configuration
app.secret_key = secrets.token_hex(16)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
# Configure SQLite database URI
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# --- Database Models ---

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Bin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bin_number = db.Column(db.String(50), unique=True, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    current_level = db.Column(db.Integer, nullable=False, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_emptied_timestamp = db.Column(db.DateTime, nullable=True) # <-- NOUVEAU CHAMP
    # Relationship to History
    history_entries = db.relationship('History', backref='bin', lazy=True, cascade="all, delete-orphan")

class History(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bin_id = db.Column(db.Integer, db.ForeignKey('bin.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    level = db.Column(db.Integer, nullable=False)

# --- Helper Functions ---

def get_default_bin():
    """Gets the first bin in the database (ID=1), assumes it's the default."""
    # Use db.session.get for primary key lookup (more efficient)
    return db.session.get(Bin, 1)

# --- Routes ---

# Middleware for authentication
def login_required(f):
    @wraps(f) # Use wraps from functools
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Veuillez vous connecter pour accéder à cette page.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles the login page."""
    if 'user_id' in session:
        return redirect(url_for('index')) # Redirect if already logged in

    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        # Use case-insensitive query for username
        user = User.query.filter(User.username.ilike(username)).first()

        if user and user.check_password(password):
            session.permanent = True
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Connexion réussie !', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            error = "Identifiants incorrects. Veuillez réessayer."

    # Keep the login template as it is (long HTML string)
    login_template = """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Smart-Trash</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');

            :root {
                /* Palette de couleurs personnalisée */
                --primary-color: #1A4D2E; /* Vert foncé principal */
                --primary-hover-color: #113822; /* Vert foncé assombri pour survol */
                
                --body-bg-gradient-start: #F3F7F2; /* Un vert très clair, presque blanc pour le fond */
                --body-bg-gradient-end: #E8F0E6;   /* Un vert clair un peu plus soutenu pour le dégradé */

                --container-bg-color: #ffffff; /* Conteneur de login blanc pour contraste */
                --container-shadow-color: rgba(0, 0, 0, 0.1);

                --text-color-primary: #1A4D2E; /* Texte principal (vert foncé) */
                --text-color-secondary: #4F6F52; /* Texte secondaire (vert moyen) */
                --text-color-labels: var(--primary-color); 
                
                --input-border-color: #A5D6A7; /* Bordure d'input en vert clair */
                --input-focus-border-color: var(--primary-color);
                --input-focus-shadow-rgb: 26, 77, 46; /* RGB de #1A4D2E */
                --input-icon-color: var(--text-color-secondary); /* #4F6F52 */
                --input-icon-focus-color: var(--primary-color); /* #1A4D2E */

                --button-text-color: #ffffff; /* Texte du bouton en blanc */
                --button-shadow-rgb: 26, 77, 46; /* RGB de #1A4D2E pour l'ombre */

                /* Couleurs des alertes (standard pour la lisibilité) */
                --alert-danger-text: #721c24;
                --alert-danger-bg: #f8d7da;
                --alert-danger-border: #f5c6cb;
                --alert-warning-text: #856404;
                --alert-warning-bg: #fff3cd;
                --alert-warning-border: #ffeeba;
                --alert-success-text: #155724; /* Ce vert est proche de votre thème */
                --alert-success-bg: #d4edda;
                --alert-success-border: #c3e6cb;
                --alert-info-text: #0c5460;
                --alert-info-bg: #d1ecf1;
                --alert-info-border: #bee5eb;
            }

            body {
                font-family: 'Roboto', sans-serif;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, var(--body-bg-gradient-start) 0%, var(--body-bg-gradient-end) 100%);
                color: var(--text-color-primary);
                line-height: 1.6;
            }
            .login-container {
                background-color: var(--container-bg-color);
                padding: 35px 40px;
                border-radius: 12px;
                box-shadow: 0 10px 25px var(--container-shadow-color);
                width: 100%;
                max-width: 430px;
                text-align: center;
            }
            .login-header {
                margin-bottom: 25px;
            }
            .login-header h1 {
                color: var(--text-color-primary);
                font-size: 26px; /* Taille du texte du titre */
                font-weight: 700;
                margin-bottom: 8px;
                display: flex; /* Permet d'aligner l'icône et le texte sur la même ligne */
                align-items: center; /* Aligne verticalement l'icône et le texte */
                justify-content: center; /* Centre l'ensemble (icône + texte) dans le h1 */
            }
            .login-header h1 .fas.fa-leaf { /* Style spécifique pour l'icône feuille dans le H1 */
                margin-right: 10px; /* Espace entre l'icône et le texte */
                color: var(--primary-color); /* Assure la couleur verte de l'icône */
                font-size: 1em; /* Taille de l'icône relative à la taille du texte H1. Ajustez si besoin (ex: 1.2em pour plus grand) */
                line-height: 1; /* Assure un bon alignement vertical si la hauteur de ligne du H1 est différente */
            }
            .login-header p {
                color: var(--text-color-secondary);
                font-size: 15px;
                margin-bottom: 20px;
            }
            .form-group {
                margin-bottom: 22px;
                text-align: left;
            }
            label {
                display: block;
                margin-bottom: 6px;
                color: var(--text-color-labels);
                font-weight: 500;
                font-size: 14px;
            }
            .input-wrapper {
                position: relative;
            }
            .input-wrapper .input-icon {
                position: absolute;
                left: 15px;
                top: 50%;
                transform: translateY(-50%);
                color: var(--input-icon-color);
                transition: color 0.3s;
            }
            input[type="text"], input[type="password"] {
                width: 100%;
                padding: 12px 15px 12px 45px;
                border: 1px solid var(--input-border-color);
                border-radius: 8px;
                font-size: 16px;
                box-sizing: border-box;
                transition: border-color 0.3s, box-shadow 0.3s;
                color: var(--text-color-primary);
                background-color: var(--container-bg-color);
            }
            input[type="text"]:focus, input[type="password"]:focus {
                border-color: var(--input-focus-border-color);
                box-shadow: 0 0 0 3px rgba(var(--input-focus-shadow-rgb), 0.25);
                outline: none;
            }
            input[type="text"]:focus ~ .input-icon,
            input[type="password"]:focus ~ .input-icon {
                color: var(--input-icon-focus-color);
            }
            .submit-button {
                background: var(--primary-color);
                color: var(--button-text-color);
                border: none;
                padding: 13px 20px;
                border-radius: 8px;
                cursor: pointer;
                font-size: 16px;
                font-weight: 500;
                width: 100%;
                transition: background-color 0.3s, transform 0.1s, box-shadow 0.3s;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                box-shadow: 0 4px 15px rgba(var(--button-shadow-rgb), 0.2);
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .submit-button i {
                margin-right: 8px;
            }
            .submit-button:hover {
                background: var(--primary-hover-color);
                box-shadow: 0 6px 20px rgba(var(--button-shadow-rgb), 0.3);
                transform: translateY(-2px);
            }
            .submit-button:active {
                transform: translateY(0px);
                box-shadow: 0 2px 10px rgba(var(--button-shadow-rgb), 0.2);
            }
            .alert {
                padding: 12px 15px;
                margin-bottom: 20px;
                border: 1px solid transparent;
                border-radius: 8px;
                font-weight: 500;
                font-size: 14px;
                text-align: left;
            }
            .alert-danger { color: var(--alert-danger-text); background-color: var(--alert-danger-bg); border-color: var(--alert-danger-border); }
            .alert-warning { color: var(--alert-warning-text); background-color: var(--alert-warning-bg); border-color: var(--alert-warning-border); }
            .alert-success { color: var(--alert-success-text); background-color: var(--alert-success-bg); border-color: var(--alert-success-border); }
            .alert-info { color: var(--alert-info-text); background-color: var(--alert-info-bg); border-color: var(--alert-info-border); }
        </style>
    </head>
    <body>
        <div class="login-container">
            <div class="login-header">
                <h1><i class="fas fa-leaf"></i>bienvenue à Smart-Trash </h1>
                <p>Gestionnaire de conteneurs  Intelligents </p>
            </div>

            {% with messages = get_flashed_messages(with_categories=true) %}
              {% if messages %}
                {% for category, message in messages %}
                  <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
              {% endif %}
            {% endwith %}

            {% if error %}
            <div class="alert alert-danger">{{ error }}</div>
            {% endif %}

            <form method="post">
                <div class="form-group">
                    <label for="username">Nom d'utilisateur</label>
                    <div class="input-wrapper">
                        <input type="text" id="username" name="username" placeholder="Entrez votre identifiant" required>
                        <i class="fas fa-user input-icon"></i>
                    </div>
                </div>
                <div class="form-group">
                    <label for="password">Mot de passe</label>
                    <div class="input-wrapper">
                        <input type="password" id="password" name="password" placeholder="Entrez votre mot de passe" required>
                        <i class="fas fa-lock input-icon"></i>
                    </div>
                </div>
                <button type="submit" class="submit-button">
                    <i class="fas fa-sign-in-alt"></i>Se connecter
                </button>
            </form>
        </div>
    </body>
    </html>
    """
    return render_template_string(login_template, error=error)


@app.route('/logout')
def logout():
    """Logs the user out."""
    session.pop('user_id', None)
    session.pop('username', None)
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('login'))

@app.route('/update', methods=['GET'])
def update_level():
    """Updates the fill level of a specific or default bin and checks for emptying event."""
    new_level = request.args.get('level', type=int)
    bin_number_param = request.args.get('bin_number')
    now = datetime.utcnow() # Get current time once

    if new_level is None or not (0 <= new_level <= 100):
        return jsonify({"error": "Le niveau doit être un entier entre 0 et 100"}), 400

    target_bin = None
    if bin_number_param:
        target_bin = Bin.query.filter_by(bin_number=bin_number_param).first()
        if not target_bin:
            return jsonify({"error": f"Poubelle {bin_number_param} non trouvée"}), 404
    else:
        target_bin = get_default_bin()
        if not target_bin:
            return jsonify({"error": "Aucune poubelle par défaut trouvée (ID=1)"}), 404

    # Get the level *before* updating
    old_level = target_bin.current_level

    # Update bin level and last updated time
    target_bin.current_level = new_level
    target_bin.last_updated = now

    # Check for emptying condition: old level >= 80 and new level <= 20
    if old_level >= 80 and new_level <= 20:
        target_bin.last_emptied_timestamp = now
        app.logger.info(f"Bin {target_bin.bin_number} emptied detected at {now}. Old level: {old_level}, New level: {new_level}")

    # Add to history only if level is critical (>= 80%)
    # Note: This adds an entry even if the level *stays* above 80%
    if new_level >= 80:
        history_entry = History(bin_id=target_bin.id, level=new_level, timestamp=now)
        db.session.add(history_entry)

    try:
        db.session.commit()
        return jsonify({
            "success": True,
            "level": new_level,
            "bin_number": target_bin.bin_number,
            "last_emptied_detected": (old_level >= 80 and new_level <= 20) # Indicate if emptying was detected in this update
        })
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating bin level: {e}")
        return jsonify({"error": "Erreur lors de la mise à jour de la base de données"}), 500


@app.route('/level', methods=['GET'])
def get_level():
    """Returns the current information for the default bin (ID=1), including last emptied time."""
    target_bin = get_default_bin()
    if not target_bin:
        return jsonify({
            "level": 0,
            "numero": "N/A",
            "adresse": "N/A",
            "historique": [],
            "authenticated": 'user_id' in session,
            "last_updated": None,
            "last_emptied": None, # <-- NOUVELLE CLE
            "error": "Poubelle par défaut (ID=1) non trouvée"
        }), 404

    # Fetch recent critical history entries
    critical_history = History.query.filter_by(bin_id=target_bin.id)\
                                    .order_by(History.timestamp.desc())\
                                    .limit(10).all()

    history_data = [{
        "timestamp": h.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "niveau": h.level
        # "numero": target_bin.bin_number # Removed, redundant as it's for the target_bin
    } for h in critical_history]

    # Format timestamps for JSON response
    last_updated_iso = target_bin.last_updated.isoformat() if target_bin.last_updated else None
    last_emptied_iso = target_bin.last_emptied_timestamp.isoformat() if target_bin.last_emptied_timestamp else None

    return jsonify({
        "level": target_bin.current_level,
        "numero": target_bin.bin_number,
        "adresse": target_bin.location,
        "historique": history_data,
        "authenticated": 'user_id' in session,
        "last_updated": last_updated_iso,
        "last_emptied": last_emptied_iso # <-- NOUVELLE CLE
    })

@app.route('/config', methods=['POST'])
@login_required
def update_config():
    """Updates the configuration of the default bin (ID=1)."""
    target_bin = get_default_bin()
    if not target_bin:
        # Use flash for user feedback, return redirect or render template
        flash('Erreur: Poubelle par défaut (ID=1) non trouvée.', 'danger')
        return redirect(url_for('index')) # Or render a config page with error

    data = request.form # Assuming form data, not JSON, based on typical web forms
    if not data:
        flash('Aucune donnée de configuration fournie.', 'warning')
        return redirect(url_for('index'))

    updated = False
    error_occurred = False

    if "numero" in data:
        new_bin_number = data["numero"].strip()
        if not new_bin_number:
            flash('Le numéro de poubelle ne peut pas être vide.', 'danger')
            error_occurred = True
        else:
            # Check if the new number is already used by *another* bin
            existing_bin = Bin.query.filter(Bin.bin_number == new_bin_number, Bin.id != target_bin.id).first()
            if existing_bin:
                flash(f"Le numéro de poubelle '{new_bin_number}' est déjà utilisé.", 'danger')
                error_occurred = True
            else:
                target_bin.bin_number = new_bin_number
                updated = True

    if "adresse" in data:
        new_location = data["adresse"].strip()
        if not new_location:
            flash("L'adresse ne peut pas être vide.", 'danger')
            error_occurred = True
        else:
            target_bin.location = new_location
            updated = True

    if updated and not error_occurred:
        try:
            db.session.commit()
            flash('Configuration de la poubelle mise à jour avec succès.', 'success')
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error updating bin config: {e}")
            flash('Erreur lors de la mise à jour de la configuration.', 'danger')
    elif not updated and not error_occurred:
        flash('Aucune modification détectée dans la configuration.', 'info')

    # Always redirect back to the main page after processing
    return redirect(url_for('index'))


@app.route('/')
@login_required
def index():
    """Serves the main dashboard page using the specific HTML file."""
    # Define the expected HTML file name within the static folder
    html_file_name = 'index(1).html'
    # Construct the full path relative to the application's static folder
    # Use app.static_folder which is configured during Flask app initialization
    html_file_path = os.path.join(app.static_folder, html_file_name)

    # Check if the file exists in the static folder
    if not os.path.exists(html_file_path):
        # If not found in static, maybe try the upload directory as a fallback?
        # Or log an error and return a proper 404
        fallback_path = os.path.join(basedir, 'upload', html_file_name) # Example fallback
        if os.path.exists(fallback_path):
             html_file_path = fallback_path
             app.logger.warning(f"HTML file found in fallback location: {fallback_path}")
        else:
            app.logger.error(f"HTML file not found in static folder ({app.static_folder}) or fallback.")
            # Return a user-friendly error page or message
            return f"Erreur: Fichier d'interface {html_file_name} introuvable.", 404

    try:
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        # Pass necessary data to the template if needed (like username)
        return render_template_string(html_content, username=session.get('username'))
    except Exception as e:
        app.logger.error(f"Error reading or rendering index file {html_file_path}: {e}")
        return "Erreur interne lors du chargement de la page principale.", 500

# --- Database Initialization Command ---
@app.cli.command('init-db')
def init_db_command():
    """Creates database tables and initializes default data."""
    global db
    try:
        with app.app_context():
            print("Attempting to create database tables...")
            db.create_all() # This creates tables based on models if they don't exist
            print("Database tables checked/created.")

            # Check and create admin user
            if User.query.filter_by(username='admin').first() is None:
                admin_user = User(username='admin')
                default_password = 'adminpassword' # CHANGE THIS IN PRODUCTION
                admin_user.set_password(default_password)
                db.session.add(admin_user)
                print(f"Admin user 'admin' created with default password: {default_password}")
            else:
                print("Admin user 'admin' already exists.")

            # Check and create default bin (ID=1)
            if db.session.get(Bin, 1) is None: # Use session.get for primary key check
                default_bin_number = "P-001"
                # Ensure the default bin number isn't already taken by another ID
                existing_bin_by_number = Bin.query.filter_by(bin_number=default_bin_number).first()
                if not existing_bin_by_number:
                    default_bin = Bin(
                        id=1,
                        bin_number=default_bin_number,
                        location="123 Rue de l'Exemple, 75000 Paris",
                        current_level=10,
                        last_emptied_timestamp=None # Initialize new field
                    )
                    db.session.add(default_bin)
                    print(f"Default bin '{default_bin_number}' (ID=1) created.")
                else:
                    # This case should ideally not happen if ID=1 is reserved, but good to handle
                    print(f"Bin with number '{default_bin_number}' already exists (ID={existing_bin_by_number.id}). Cannot create default bin with ID 1 using this number.")
            else:
                print("Default bin (ID=1) already exists.")

            db.session.commit()
            print("Database initialization/check complete.")
    except Exception as e:
        db.session.rollback()
        print(f"Error during database initialization: {e}")
        app.logger.error(f"Database initialization failed: {e}", exc_info=True)

# --- Utility function to copy HTML (ensure it copies to the correct static folder) ---
def ensure_static_files():
    static_dir = app.static_folder # Use the configured static folder path
    if not static_dir:
        app.logger.error("Static folder not configured for the Flask app.")
        return

    if not os.path.exists(static_dir):
        try:
            os.makedirs(static_dir)
            print(f"Created static directory at: {static_dir}")
        except OSError as e:
             app.logger.error(f"Failed to create static directory {static_dir}: {e}")
             return # Cannot proceed without static dir

    source_html_filename = 'index(1).html' # The original filename
    source_html_path = os.path.join(basedir, source_html_filename) # Assume it's in the app root
    dest_html_path = os.path.join(static_dir, source_html_filename)

    # Copy only if source exists and destination doesn't, or if source is newer
    copy_needed = False
    if os.path.exists(source_html_path):
        if not os.path.exists(dest_html_path):
            copy_needed = True
        else:
            # Optional: Check if source is newer than destination
            # source_mtime = os.path.getmtime(source_html_path)
            # dest_mtime = os.path.getmtime(dest_html_path)
            # if source_mtime > dest_mtime:
            #     copy_needed = True
            pass # For now, just copy if missing

    if copy_needed:
        import shutil
        try:
            # Use the final corrected HTML file as source
            final_html_source = "/home/ubuntu/index_final.html"
            if os.path.exists(final_html_source):
                 shutil.copy2(final_html_source, dest_html_path) # copy2 preserves metadata
                 print(f"Copied {final_html_source} to {dest_html_path}")
            else:
                 print(f"Error: Source file {final_html_source} not found. Cannot copy.")
                 app.logger.error(f"Source file {final_html_source} not found during static file copy.")

        except Exception as e:
            print(f"Error copying HTML file: {e}")
            app.logger.error(f"Failed to copy {source_html_filename} to static folder: {e}")
    elif not os.path.exists(source_html_path):
        print(f"Warning: Original source HTML file not found at {source_html_path}. Cannot copy to static folder.")
        # If the destination also doesn't exist, the app might fail later in the index route
        if not os.path.exists(dest_html_path):
             app.logger.warning(f"Destination HTML file {dest_html_path} also missing.")

# --- Main Execution ---
if __name__ == '__main__':
    # Ensure static files are in place *before* initializing DB or running app
    ensure_static_files()

    # Initialize DB within app context
    with app.app_context():
        try:
            # Check if DB file exists. If not, init-db will create it.
            db_file_path = os.path.join(basedir, 'database.db')
            if not os.path.exists(db_file_path):
                 print("Database file not found. Running init-db...")
                 init_db_command()
            else:
                # If DB file exists, check if tables are present
                inspector = db.inspect(db.engine)
                if not inspector.has_table("bin"): # Check for a key table like 'bin'
                    print("Database tables seem missing. Running init-db...")
                    init_db_command()
                else:
                    print("Database tables exist. Checking default data...")
                    # Run init-db anyway to ensure default data consistency and add new column if needed
                    init_db_command()

        except Exception as e:
            app.logger.error(f"Error during DB check/initialization in main: {e}. Attempting init-db as fallback.")
            try:
                 init_db_command()
            except Exception as init_e:
                 app.logger.error(f"Fallback init-db also failed: {init_e}")
                 print("CRITICAL: Database initialization failed. The application might not work correctly.")

    # Run the Flask development server
    # Use debug=False for production generally, True for development
    # host='0.0.0.0' makes it accessible on the network
    app.run(host='0.0.0.0', port=5000, debug=True)
