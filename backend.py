import os
import json
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, Response

base_dir = os.path.abspath(os.path.dirname(__file__))
template_dir = os.path.join(base_dir, 'templates')

app = Flask(__name__, template_folder=template_dir)
app.secret_key = 'sih_samanvay_secret_key'

DB_FILE = os.path.join(base_dir, 'database.json')

def load_users():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_user(user_data):
    users = load_users()
    # Overwrite record if user registers again with same phone
    users = [u for u in users if u.get('phone') != user_data.get('phone')]
    users.append(user_data)
    with open(DB_FILE, 'w') as f:
        json.dump(users, f, indent=4)

# Security decorator for Admin Panel
def check_auth(username, password):
    return username == 'admin' and password == '~~'

def authenticate():
    return Response(
        'Could not verify your access level for Samanvay Admin Panel.\n'
        'You must login with proper credentials.', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            return render_template('register.html', error="Passwords do not match. Please re-enter.")

        available_docs = request.form.getlist('owned_docs')
        
        user_data = {
            'full_name': request.form.get('full_name'),
            'address': request.form.get('address'),
            'phone': request.form.get('phone'),
            'password': password,
            'pin': request.form.get('pin'),
            'state': request.form.get('state', 'Maharashtra'),
            'caste': request.form.get('caste'),
            'gender': request.form.get('gender'),
            'income': request.form.get('income'),
            'profession': request.form.get('profession'),
            'owned_docs': available_docs
        }
        
        session['user_profile'] = user_data
        save_user(user_data)

        return redirect(url_for('document_vault'))
        
    return render_template('register.html')

@app.route('/document-vault', methods=['GET', 'POST'])
def document_vault():
    user_profile = session.get('user_profile')
    if not user_profile:
        return redirect(url_for('register'))
        
    if request.method == 'POST':
        owned_docs = user_profile.get('owned_docs', [])
        missing_docs = []

        doc_field_map = {
            'aadhaar': 'file_aadhaar',
            'income_cert': 'file_income',
            'caste_cert': 'file_caste',
            'domicile': 'file_domicile'
        }

        for doc in owned_docs:
            field_name = doc_field_map.get(doc)
            file = request.files.get(field_name)
            if not file or file.filename == '':
                missing_docs.append(doc)

        if missing_docs:
            return render_template(
                'vault_upload.html', 
                user=user_profile, 
                error="Please upload all selected documents before proceeding."
            )

        session['vault_active'] = True
        return redirect(url_for('dashboard'))
        
    return render_template('vault_upload.html', user=user_profile)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form.get('phone')
        password = request.form.get('password')
        
        users = load_users()
        matched_user = next((u for u in users if u.get('phone') == phone and u.get('password') == password), None)

        if matched_user:
            session['user_profile'] = matched_user
            session['vault_active'] = True
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid Mobile Number or Password.")

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    user_profile = session.get('user_profile')
    if not user_profile:
        return redirect(url_for('login'))
    return render_template('dashboard.html', profile=user_profile)

@app.route('/admin/database')
@requires_auth
def admin_database():
    users = load_users()
    return render_template('admin_db.html', users=users)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)