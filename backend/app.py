from flask import Flask, render_template, request, redirect, session, jsonify
import pickle, os, sqlite3
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

# 🔥 OCR import (IMPORTANT)
import pytesseract
from PIL import Image

# 👉 Windows users ke liye (adjust if needed)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

app = Flask(__name__, template_folder='../frontend')
app.secret_key = "secret123"

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ================= DATABASE ================= #
def get_db():
    return sqlite3.connect('database.db')

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            email TEXT,
            password TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ================= MODEL ================= #
try:
    with open('model.pkl', 'rb') as f:
        model = pickle.load(f)
except:
    model = None

# ================= ROUTES ================= #

@app.route('/')
def home():
    return render_template('login.html')


@app.route('/register')
def register_page():
    return render_template('register.html')


# 🔹 REGISTER
@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    confirm = request.form.get('confirm_password')

    if not username or not email or not password:
        return render_template('register.html', error="All fields required ❌")

    if password != confirm:
        return render_template('register.html', error="Passwords do not match ❌")

    hashed_password = generate_password_hash(password)

    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                    (username, email, hashed_password))
        conn.commit()
    except:
        return render_template('register.html', error="User already exists ❌")
    finally:
        conn.close()

    return redirect('/')


@app.route('/login', methods=['POST'])
def login():
    username_or_email = request.form.get('username')
    password = request.form.get('password')

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT username, password FROM users WHERE username=? OR email=?",
        (username_or_email, username_or_email)
    )

    user = cur.fetchone()
    conn.close()

    if user and check_password_hash(user[1], password):
        session['user'] = user[0]
        return redirect('/dashboard')

    return render_template(
        'login.html',
        error="Invalid Username/Email or Password ❌"
    )


# 🔹 DASHBOARD
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/')
    return render_template('index.html')


# 🔹 DETECT PAGE
@app.route('/detect')
def detect():
    if 'user' not in session:
        return redirect('/')
    return render_template('detect.html')


# ================= FRAUD DETECTION ================= #

# 🔹 ML Prediction
@app.route('/predict', methods=['POST'])
def predict():
    if 'user' not in session:
        return redirect('/')

    if model is None:
        return render_template('result.html', result="Model not loaded ❌")

    try:
        amount = float(request.form.get('amount', 0))
        step = float(request.form.get('step', 1))

        prediction = model.predict([[amount, step]])

        result = "❌ Fraud Transaction Detected" if prediction[0] == 1 else "✅ Safe Transaction"

        return render_template('result.html', result=result)

    except Exception as e:
        return render_template('result.html', result=f"Error: {str(e)}")


# 🔹 QR SCAN
@app.route('/scan-qr', methods=['POST'])
def scan_qr():
    data = request.json.get('data', '')
    data_lower = data.lower()

    if data_lower.startswith("upi://pay"):
        import urllib.parse as urlparse
        parsed = urlparse.urlparse(data)
        params = urlparse.parse_qs(parsed.query)

        upi_id = params.get('pa', [''])[0]
        name = params.get('pn', [''])[0]

        if not upi_id:
            result = "⚠️ Invalid UPI QR"
        elif any(word in data_lower for word in ["urgent", "click", "offer", "free"]):
            result = "⚠️ Suspicious QR"
        else:
            result = f"✅ Safe UPI | {name} | {upi_id}"

    elif data_lower.startswith("http"):
        result = "⚠️ External Link"

    else:
        result = "✅ Normal QR"

    return jsonify({'result': result})


# 🔹 IMAGE SCAN (FIXED)
@app.route('/scan-image', methods=['POST'])
def scan_image():
    if 'file' not in request.files:
        return render_template('result.html', result="No file ❌")

    file = request.files['file']

    if file.filename == '':
        return render_template('result.html', result="No file selected ❌")

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    try:
        # 🔥 OCR text extract
        text = pytesseract.image_to_string(Image.open(filepath)).lower()

        print("📄 OCR TEXT:", text)  # debug

        # 🔥 Better detection
        fraud_keywords = ["urgent", "pay now", "click", "lottery", "free", "offer"]

        if any(word in text for word in fraud_keywords):
            result = "❌ Fraud Detected from Image"
        else:
            result = "✅ Image Looks Safe"

        return render_template('result.html', result=result)

    except Exception as e:
        return render_template('result.html', result=f"OCR Error: {str(e)}")


# 🔹 LOGOUT
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')


# ================= RUN ================= #
if __name__ == "__main__":
    app.run(debug=True)