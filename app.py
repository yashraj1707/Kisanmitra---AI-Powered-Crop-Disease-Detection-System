from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
import os, json, datetime, hashlib, sqlite3
import numpy as np
from PIL import Image
import io, base64
import smtplib, threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

app = Flask(__name__)
app.secret_key = "kisanmitra_secret_2024"
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ── Email Configuration ───────────────────────────────────────────────────────
# KisanMitra's sender Gmail account — fill in once and forget:
EMAIL_USER      = 'kisanmitrapune@gmail.com'   # ← replace with your Gmail
EMAIL_PASS      = 'vsak xawz edfk grmh'    # ← replace with your Gmail App Password
EMAIL_FROM_NAME = 'KisanMitra'

def send_email(to_email, subject, html_body):
    """Send an HTML email in a background thread so it never blocks the request."""
    def _send():
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From']    = f'{EMAIL_FROM_NAME} <{EMAIL_USER}>'
            msg['To']      = to_email
            msg.attach(MIMEText(html_body, 'html', 'utf-8'))
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(EMAIL_USER, EMAIL_PASS)
                server.sendmail(EMAIL_USER, to_email, msg.as_string())
        except Exception as e:
            print(f'[KisanMitra Email Error] {e}')
    threading.Thread(target=_send, daemon=True).start()


def email_prediction_report(user, module, result):
    """Send a beautiful prediction report email to the user."""
    status_color  = '#16a34a' if result['is_healthy'] else '#dc2626'
    status_icon   = '✅' if result['is_healthy'] else '⚠️'
    severity_map  = {'Low': '#16a34a', 'Medium': '#d97706', 'High': '#dc2626', 'None': '#16a34a'}
    sev_color     = severity_map.get(result.get('severity', 'Low'), '#d97706')
    treatment     = result.get('treatment', {})

    def to_list(val):
        if isinstance(val, list):
            return val
        if isinstance(val, str) and val:
            return [item.strip() for item in val.replace('. ', '.|').replace('.', '.|').split('|') if item.strip()]
        return []

    cure_lines    = ''.join(
        f'<li style="margin-bottom:6px;color:#374151;">{c}</li>'
        for c in to_list(treatment.get('cure') or treatment.get('treatment', ''))
    )
    prevention_lines = ''.join(
        f'<li style="margin-bottom:6px;color:#374151;">{p}</li>'
        for p in to_list(treatment.get('prevention', ''))
    )
    html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f0fdf4;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0fdf4;padding:32px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:white;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,.08);">

        <!-- Header -->
        <tr><td style="background:linear-gradient(135deg,#14532d,#166534);padding:32px 40px;text-align:center;">
          <div style="font-size:2.2rem;margin-bottom:8px;">🌱</div>
          <h1 style="margin:0;color:white;font-size:1.6rem;font-weight:800;letter-spacing:-0.5px;">KisanMitra</h1>
          <p style="margin:4px 0 0;color:rgba(255,255,255,.7);font-size:.9rem;">किसान मित्र — Smart Crop Disease Detection</p>
        </td></tr>

        <!-- Greeting -->
        <tr><td style="padding:32px 40px 0;">
          <p style="margin:0;font-size:1rem;color:#374151;">Hi <strong>{user['name']}</strong> 👋,</p>
          <p style="margin:8px 0 0;color:#6b7280;font-size:.95rem;">Here is your prediction report for <strong style="color:#166534;">{module.title()}</strong>.</p>
        </td></tr>

        <!-- Result Card -->
        <tr><td style="padding:24px 40px;">
          <div style="background:#f8fafc;border:2px solid {status_color};border-radius:14px;padding:24px;text-align:center;">
            <div style="font-size:2.5rem;margin-bottom:8px;">{status_icon}</div>
            <div style="font-size:1.4rem;font-weight:800;color:{status_color};margin-bottom:4px;">{result['disease']}</div>
            <div style="font-size:.85rem;color:#6b7280;">Confidence: <strong style="color:#111827;">{result['confidence']}%</strong>
              &nbsp;|&nbsp; Severity: <strong style="color:{sev_color};">{result.get('severity','—')}</strong>
            </div>
          </div>
        </td></tr>

        <!-- Treatment -->
        {"" if result['is_healthy'] else f'''
        <tr><td style="padding:0 40px 24px;">
          <h3 style="margin:0 0 12px;color:#166534;font-size:1rem;">💊 Recommended Treatment</h3>
          <ul style="margin:0 0 16px;padding-left:20px;">{cure_lines}</ul>
          <h3 style="margin:0 0 12px;color:#166534;font-size:1rem;">🛡️ Prevention Tips</h3>
          <ul style="margin:0;padding-left:20px;">{prevention_lines}</ul>
        </td></tr>'''}

        <!-- Credits -->
        <tr><td style="padding:0 40px 24px;">
          <div style="background:#fef3c7;border-radius:10px;padding:14px 18px;display:flex;align-items:center;gap:10px;">
            <span style="font-size:1.2rem;">⚡</span>
            <span style="font-size:.88rem;color:#92400e;">
              <strong>5 credits</strong> used for this scan &nbsp;·&nbsp;
              <strong>{user['credits'] - 5}</strong> credits remaining
            </span>
          </div>
        </td></tr>

        <!-- CTA -->
        <tr><td style="padding:0 40px 32px;text-align:center;">
          <a href="http://127.0.0.1:5000/predict/{module}" style="display:inline-block;background:linear-gradient(135deg,#16a34a,#14532d);color:white;text-decoration:none;padding:12px 28px;border-radius:24px;font-weight:700;font-size:.95rem;margin-bottom:12px;">🔍 Scan Another Leaf</a>
          <br>
          <a href="http://127.0.0.1:5000/plans" style="font-size:.82rem;color:#166534;text-decoration:none;">⭐ Upgrade for more credits →</a>
        </td></tr>

        <!-- Footer -->
        <tr><td style="background:#f8fafc;border-top:1px solid #e5e7eb;padding:20px 40px;text-align:center;">
          <p style="margin:0;font-size:.78rem;color:#9ca3af;">© 2026 KisanMitra · Pune, Maharashtra · Built for Indian Farmers ❤️</p>
          <p style="margin:4px 0 0;font-size:.75rem;color:#d1d5db;">You received this because you made a prediction on KisanMitra.</p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""
    send_email(user['email'], f'🌿 KisanMitra — Your {module.title()} Scan Report', html)


def email_plan_purchased(user, plan):
    """Send a plan purchase confirmation email."""
    plan_icons = {'basic': '⭐', 'pro': '🚀', 'enterprise': '🏢'}
    icon = plan_icons.get(plan['id'], '✅')
    features_en = plan['features'].get('en', [])
    feat_rows = ''.join(
        f'<tr><td style="padding:8px 0;border-bottom:1px solid #f0fdf4;color:#374151;font-size:.9rem;">✅&nbsp; {f}</td></tr>'
        for f in features_en
    )
    html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f0fdf4;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0fdf4;padding:32px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:white;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,.08);">

        <!-- Header -->
        <tr><td style="background:linear-gradient(135deg,#14532d,#166534);padding:32px 40px;text-align:center;">
          <div style="font-size:2.5rem;margin-bottom:8px;">{icon}</div>
          <h1 style="margin:0;color:white;font-size:1.6rem;font-weight:800;">Plan Activated!</h1>
          <p style="margin:6px 0 0;color:rgba(255,255,255,.75);font-size:.9rem;">KisanMitra — किसान मित्र</p>
        </td></tr>

        <!-- Greeting -->
        <tr><td style="padding:32px 40px 0;">
          <p style="margin:0;font-size:1rem;color:#374151;">Hi <strong>{user['name']}</strong> 👋,</p>
          <p style="margin:10px 0 0;color:#6b7280;font-size:.95rem;">
            Your <strong style="color:#166534;">{plan['id'].title()} Plan</strong> is now active. Thank you for supporting KisanMitra! 🎉
          </p>
        </td></tr>

        <!-- Plan Summary -->
        <tr><td style="padding:24px 40px;">
          <div style="background:linear-gradient(135deg,#f0fdf4,#dcfce7);border:2px solid #16a34a;border-radius:14px;padding:24px;">
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;">
              <span style="font-size:2rem;">{icon}</span>
              <div>
                <div style="font-size:1.3rem;font-weight:800;color:#14532d;">{plan['id'].title()} Plan</div>
                <div style="font-size:1.5rem;font-weight:900;color:#166534;">₹{plan['price']}<span style="font-size:.9rem;font-weight:400;color:#6b7280;">/month</span></div>
              </div>
            </div>
            <div style="background:#dcfce7;border-radius:8px;padding:10px 14px;font-size:.9rem;color:#14532d;font-weight:600;margin-bottom:16px;">
              ⚡ {plan['credits']} Credits added to your account
            </div>
            <table width="100%" cellpadding="0" cellspacing="0">
              {feat_rows}
            </table>
          </div>
        </td></tr>

        <!-- CTA -->
        <tr><td style="padding:0 40px 32px;text-align:center;">
          <a href="http://127.0.0.1:5000/predict" style="display:inline-block;background:linear-gradient(135deg,#16a34a,#14532d);color:white;text-decoration:none;padding:13px 32px;border-radius:24px;font-weight:700;font-size:1rem;">
            🌿 Start Scanning Now
          </a>
          <br><br>
          <a href="http://127.0.0.1:5000/profile" style="font-size:.82rem;color:#166534;text-decoration:none;">View your profile →</a>
        </td></tr>

        <!-- Footer -->
        <tr><td style="background:#f8fafc;border-top:1px solid #e5e7eb;padding:20px 40px;text-align:center;">
          <p style="margin:0;font-size:.78rem;color:#9ca3af;">© 2026 KisanMitra · Pune, Maharashtra · Built for Indian Farmers ❤️</p>
          <p style="margin:4px 0 0;font-size:.75rem;color:#d1d5db;">This is a payment confirmation for your KisanMitra subscription.</p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""
    send_email(user['email'], f'{icon} KisanMitra — {plan["id"].title()} Plan Activated!', html)

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

FREE_CREDITS = 200
CREDITS_PER_PREDICTION = 5

# ── Database ──────────────────────────────────────────────────────────────────
def get_db():
    db = sqlite3.connect('kisanmitra.db')
    db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            credits INTEGER DEFAULT 200,
            plan TEXT DEFAULT 'free',
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            message TEXT NOT NULL,
            rating INTEGER DEFAULT 5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS contact (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            subject TEXT,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            module TEXT NOT NULL,
            disease TEXT,
            confidence REAL,
            image_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    db.commit()
    db.close()

init_db()

# ── Migrate existing DB: add is_admin if missing ─────────────────────────────
try:
    _mdb = get_db()
    _mdb.execute('ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0')
    _mdb.commit()
    _mdb.close()
except Exception:
    pass  # Column already exists

# ── Migrate existing DB: add profile_photo if missing ────────────────────────
try:
    _mdb = get_db()
    _mdb.execute("ALTER TABLE users ADD COLUMN profile_photo TEXT DEFAULT NULL")
    _mdb.commit()
    _mdb.close()
except Exception:
    pass  # Column already exists

def is_admin_user(user):
    """Return True if user has admin privileges."""
    if not user:
        return False
    try:
        return bool(user['is_admin'])
    except Exception:
        return False

def require_admin(user):
    """Return True if user is admin, else False."""
    return is_admin_user(user)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_current_user():
    if 'user_id' not in session:
        return None
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id=?', (session['user_id'],)).fetchone()
    db.close()
    return user

# ── i18n translations ─────────────────────────────────────────────────────────
TRANSLATIONS = {
    'en': {
        # ── Nav ──
        'nav_home': 'Home', 'nav_predict': 'Predict', 'nav_library': 'Library',
        'nav_weather': 'Weather', 'nav_calendar': 'Calendar', 'nav_about': 'About',
        'nav_contact': 'Contact', 'nav_feedback': 'Feedback',
        'nav_login': 'Login', 'nav_signup': 'Sign Up', 'nav_logout': 'Logout',
        'nav_profile': 'My Profile',
        'credits_label': 'Credits', 'credits_remaining': 'Credits Remaining',
        'credits_used': 'Credits Used', 'each_prediction': '5 credits per prediction',
        'no_credits_title': 'Credits Exhausted!',
        'no_credits_msg': 'You have used all your free credits. Upgrade to a plan to continue.',
        'upgrade_now': 'Upgrade Now',
        # ── Footer ──
        'footer_tagline': 'AI-powered plant disease detection for Indian farmers. Protecting crops, securing livelihoods.',
        'footer_resources': 'Resources', 'footer_plans': 'Plans & Pricing', 'footer_rights': '© 2024 KisanMitra. Built with ❤️ for Indian Farmers.',
        # ── Hero / Home ──
        'hero_badge': '🌿 AI-Powered Crop Protection Platform',
        'hero_title': 'Protect Your Crops with Smart AI Detection',
        'hero_subtitle': 'KisanMitra helps farmers instantly identify diseases in 8+ crops using advanced machine learning. Upload a leaf photo, get diagnosis + treatment in seconds.',
        'hero_btn_detect': 'Detect Disease Now', 'hero_btn_library': 'Disease Library',
        'stat_crops': 'Crop Modules', 'stat_predictions': 'Predictions Made', 'stat_diseases': 'Diseases Covered',
        'home_why_label': 'Why KisanMitra', 'home_why_title': 'Smart Farming, Made Simple',
        'home_why_sub': 'Combining AI with agricultural expertise to protect your harvest and secure your livelihood',
        'feat1_title': 'AI-Powered Detection', 'feat1_desc': 'Deep learning models trained on thousands of real crop images deliver accurate disease identification in under 5 seconds.',
        'feat2_title': 'Instant Treatment Advice', 'feat2_desc': 'Get actionable treatment recommendations, pesticide names, and dosages specific to the identified disease — in plain language.',
        'feat3_title': '8 Crop Modules', 'feat3_desc': 'Supports Tomato, Potato, Corn, Grape, Apple, Rice, Wheat, and Mango — covering major Indian and export crops.',
        'feat4_title': 'Weather Advisory', 'feat4_desc': 'Real-time weather data linked to disease risk forecasting. Know when conditions favor fungal or bacterial outbreaks.',
        'feat5_title': 'Crop Calendar', 'feat5_desc': 'Month-by-month sowing, growth, and harvest schedules for major Indian crops to help plan agricultural operations.',
        'feat6_title': 'Disease Library', 'feat6_desc': 'Comprehensive encyclopedia of 38+ crop diseases with symptoms, causes, severity ratings, and prevention strategies.',
        'modules_label': 'Detection Modules', 'modules_title': 'Choose Your Crop',
        'modules_sub': 'Select the crop and upload a leaf or fruit image for instant AI-powered disease detection',
        'detects': 'Detects', 'diseases': 'diseases', 'conditions': 'conditions',
        'how_label': 'Process', 'how_title': 'How It Works', 'how_sub': 'Diagnose and treat your crops in 3 simple steps',
        'step1_title': '1. Upload Image', 'step1_desc': 'Take a clear photo of the affected leaf, fruit, or stem and upload it to the KisanMitra platform.',
        'step2_title': '2. AI Analysis', 'step2_desc': 'Our trained deep learning model analyzes the image and identifies the disease with confidence score.',
        'step3_title': '3. Get Treatment', 'step3_desc': 'Receive detailed treatment recommendations, preventive measures, and severity assessment instantly.',
        'impact_label': 'Impact', 'impact_title': 'Our Numbers',
        'accuracy_label': '% Accuracy (Tomato)', 'total_pred_label': 'Total Predictions',
        'cta_title': 'Start Protecting Your Crops Today',
        'cta_sub': 'Join thousands of farmers who use KisanMitra to detect and treat crop diseases before they spread.',
        'try_detection': 'Try Detection Now', 'share_feedback': 'Share Feedback',
        # ── Auth ──
        'login_title': 'Login to KisanMitra', 'login_email': 'Email Address',
        'login_password': 'Password', 'login_btn': 'Login', 'login_no_account': "Don't have an account?",
        'signup_title': 'Create Your Account', 'signup_name': 'Full Name',
        'signup_email': 'Email Address', 'signup_password': 'Password',
        'signup_confirm': 'Confirm Password', 'signup_btn': 'Create Account',
        'signup_free_credits': 'You get 200 FREE credits on signup!',
        'signup_has_account': 'Already have an account?',
        # ── Plans ──
        'plan_free': 'Free', 'plan_basic': 'Basic', 'plan_pro': 'Pro', 'plan_enterprise': 'Enterprise',
        'per_month': '/month', 'choose_plan': 'Choose Your Plan',
        # ── Detection ──
        'detect_btn': 'Detect Disease', 'upload_image': 'Upload Crop Image',
        'analyzing': 'Analyzing your crop image...', 'result_disease': 'Detected Disease',
        'result_confidence': 'Confidence', 'result_treatment': 'Treatment',
        'result_cause': 'Cause', 'result_symptoms': 'Symptoms',
        'result_prevention': 'Prevention', 'result_severity': 'Severity',
        'healthy_msg': 'Your crop appears healthy! 🎉',
        'login_required': 'Please login or sign up to use disease detection.',
        'login_to_predict': 'Login to Predict', 'signup_to_predict': 'Sign Up Free',
        'predict_label': 'AI Detection', 'predict_title': '🔬 Crop Disease Detection',
        'predict_sub': 'Select your crop below and upload a leaf/fruit image for instant AI-powered disease diagnosis',
        'predict_tip': '📷 <strong>Tip:</strong> For best results, take a clear close-up photo of the affected area in good lighting. Avoid blurry images.',
        'step1_label': 'Step 1', 'choose_crop_title': 'Choose Your Crop',
        'choose_crop_sub': 'Hover over a crop to preview its info, then click to start detection',
        'hover_crop': 'Hover over a crop', 'hover_crop_sub': 'to see ideal growing conditions and common diseases',
        'crop_info': 'CROP INFO', 'temperature': 'Temperature', 'soil': 'Soil',
        'water': 'Water', 'season': 'Season', 'common_diseases': 'Common Diseases',
        'result_title': 'Detection Result', 'result_crop': 'Crop', 'high_conf': 'High Confidence',
        'mod_conf': 'Moderate Confidence', 'low_conf': 'Low Confidence', 'try_another': 'Try Another',
        # ── Disease Library ──
        'lib_label': 'Encyclopedia', 'lib_title': '📚 Crop Disease Library',
        'lib_sub': 'Comprehensive reference for 38+ crop diseases — symptoms, causes, treatments, and prevention',
        'all_crops': '🌿 All Crops', 'pathogen_cause': 'PATHOGEN / CAUSE', 'severity_label': 'SEVERITY',
        'symptoms_label': 'SYMPTOMS', 'treatment_prev': 'Treatment & Prevention',
        'treatment_label': 'TREATMENT', 'prevention_label': 'PREVENTION',
        'detect_this': 'Detect This Disease',
        # ── Weather ──
        'weather_label': 'Module 9', 'weather_title': '🌦️ Weather Advisory',
        'weather_sub': 'Real-time weather data with crop disease risk advisory for your region',
        'weather_placeholder': 'Enter city (e.g. Pune, Nashik, Nagpur)',
        'get_weather': 'Get Weather', 'humidity': 'HUMIDITY', 'wind': 'WIND', 'uv_index': 'UV INDEX',
        'disease_advisory': '🌿 Crop Disease Advisory',
        'risk_guide_title': '📊 Weather-Disease Risk Guide',
        'condition': 'Condition', 'risk_level': 'Risk Level', 'likely_disease': 'Likely Disease',
        'action': 'Action',
        'weather_tip_title': '🌱 Crop Advisory Tips',
        'weather_tip1': 'Spray fungicide preventively when humidity > 75% for 3+ consecutive days.',
        'weather_tip2': 'Increase irrigation frequency when temperatures exceed 35°C.',
        'weather_tip3': 'Monitor for rust diseases during cool nights (< 15°C) in wheat season.',
        'weather_tip4': 'Avoid overhead irrigation when leaf wetness duration exceeds 6 hours.',
        'adv_high_humidity': '⚠️ High humidity: Risk of fungal diseases. Apply preventive fungicide.',
        'adv_high_temp': '🌡️ High temperature: Ensure adequate irrigation and shade for sensitive crops.',
        'adv_normal': '✅ Favorable weather conditions for crop growth.',
        # ── Crop Calendar ──
        'cal_label': 'Module 10', 'cal_title': '📅 Crop Calendar',
        'cal_sub': 'Month-wise sowing, growing, and harvesting guide for major Indian crops',
        'cal_heading': 'India Crop Calendar 2024',
        'cal_legend': 'S = Sow | G = Grow | H = Harvest | — = Off Season',
        'cal_sow': 'Sowing', 'cal_grow': 'Growing', 'cal_harvest': 'Harvest', 'cal_off': 'Off Season',
        'crop_col': 'Crop',
        'kharif_title': '☀️ Kharif Season (Jun–Oct)',
        'kharif_desc': 'Monsoon crops. High humidity and rainfall creates ideal conditions for fungal diseases.',
        'kharif_r1': '🔴 High risk: Late Blight, Leaf Mold',
        'kharif_r2': '🟡 Medium: Bacterial diseases',
        'kharif_r3': '💊 Apply preventive fungicides',
        'rabi_title': '❄️ Rabi Season (Nov–Mar)',
        'rabi_desc': 'Winter crops. Cool nights with low humidity, but rust and mildew remain concerns.',
        'rabi_r1': '🔴 High risk: Rust diseases (Wheat)',
        'rabi_r2': '🟡 Medium: Powdery Mildew',
        'rabi_r3': '💊 Monitor and spray Propiconazole',
        # ── About ──
        'about_title': '🌱 About KisanMitra',
        'about_sub': 'AI-powered plant disease detection for Indian farmers — our mission, team, and technology',
        'our_mission': 'Our Mission',
        'about_mission_title': 'Empowering Farmers with Smart Technology',
        'about_p1': 'India loses 15–20% of its agricultural output to crop diseases every year. KisanMitra is built to change that. By combining deep learning AI with accessible mobile technology, we help farmers identify diseases instantly and take precise action before their crops are destroyed.',
        'about_p2': 'Our platform covers 8 major crop types with 38+ diseases, providing not just detection but complete treatment guidance, weather advisory, and crop calendars — all in one place.',
        'try_detection_btn': 'Try Detection', 'view_library_btn': 'View Library',
        'crops_covered': 'Crops Covered', 'accuracy_stat': 'Accuracy', 'built_for': 'Built For', 'farmers': 'Farmers',
        'the_team': 'The Team', 'team_title': 'Project Developers',
        'team_sub': 'Final Year Computer Engineering students building technology for Bharat\'s farmers',
        'dev1_name': 'Developer 1', 'dev1_role': 'Full Stack + ML Engineer',
        'dev1_bio': 'Responsible for model training, backend API, and database design',
        'dev2_name': 'Developer 2', 'dev2_role': 'Frontend + UI/UX Designer',
        'dev2_bio': 'Responsible for web design, templates, user experience and testing',
        'tech_label': 'Technology', 'tech_title': 'Tech Stack',
        # ── Contact ──
        'contact_title': '📬 Contact Us',
        'contact_sub': 'Have questions or need support? We\'re here to help farmers across India',
        'send_message': 'Send a Message',
        'contact_form_sub': 'Fill the form below and we\'ll respond within 24 hours',
        'full_name': 'Full Name *', 'email_label': 'Email *', 'phone_label': 'Phone',
        'subject_label': 'Subject', 'message_label': 'Message *',
        'subj_general': 'General Inquiry', 'subj_support': 'Technical Support',
        'subj_detection': 'Disease Detection Help', 'subj_research': 'Research Collaboration',
        'subj_bug': 'Report a Bug',
        'msg_placeholder': 'Describe your query...',
        'send_btn': 'Send Message',
        'get_in_touch': 'Get in Touch', 'reach_us': 'Reach us through any of these channels',
        'phone_hours': 'Phone (Mon–Sat, 9AM–6PM)',
        'location_label': 'Location', 'location_val': 'Pune, Maharashtra, India',
        # ── Feedback ──
        'feedback_title': '⭐ User Feedback',
        'feedback_sub': 'Help us improve KisanMitra by sharing your experience',
        'share_feedback_title': 'Share Your Feedback',
        'feedback_form_sub': 'Your experience helps us serve farmers better',
        'your_rating': 'Your Rating', 'your_message': 'Your Message *',
        'msg_placeholder_fb': 'Tell us about your experience with KisanMitra...',
        'submit_feedback': 'Submit Feedback',
        'why_feedback': 'Why Your Feedback Matters',
        'fb_reason1': '🌱 Helps improve model accuracy',
        'fb_reason2': '🤝 Shapes future crop modules',
        'fb_reason3': '📊 Used in project evaluation',
        'fb_reason4': '🚀 Drives platform improvements',
        'platform_stats': 'Platform Stats',
        'satisfaction': '% Satisfaction', 'feedbacks_count': 'Feedbacks',
        'community_label': 'Community', 'what_farmers_say': 'What Farmers Say',
        # ── Profile ──
        'profile_title': 'My Profile', 'total_scans': 'Total Scans',
        'member_since': 'Member Since', 'current_plan': 'Current Plan',
        'scan_history': 'Scan History', 'no_scans': 'No scans yet',
    },
    'hi': {
        # ── Nav ──
        'nav_home': 'होम', 'nav_predict': 'पहचानें', 'nav_library': 'पुस्तकालय',
        'nav_weather': 'मौसम', 'nav_calendar': 'कैलेंडर', 'nav_about': 'परिचय',
        'nav_contact': 'संपर्क', 'nav_feedback': 'प्रतिक्रिया',
        'nav_login': 'लॉगिन', 'nav_signup': 'साइन अप', 'nav_logout': 'लॉगआउट',
        'nav_profile': 'मेरी प्रोफाइल',
        'credits_label': 'क्रेडिट', 'credits_remaining': 'बचे हुए क्रेडिट',
        'credits_used': 'उपयोग किए गए क्रेडिट', 'each_prediction': 'प्रति पहचान 5 क्रेडिट',
        'no_credits_title': 'क्रेडिट समाप्त!',
        'no_credits_msg': 'आपके सभी मुफ्त क्रेडिट समाप्त हो गए हैं। जारी रखने के लिए कोई प्लान खरीदें।',
        'upgrade_now': 'अभी अपग्रेड करें',
        # ── Footer ──
        'footer_tagline': 'भारतीय किसानों के लिए AI-आधारित पौधे रोग पहचान। फसलों की सुरक्षा, आजीविका की रक्षा।',
        'footer_resources': 'संसाधन', 'footer_plans': 'योजनाएं और मूल्य', 'footer_rights': '© 2024 किसानमित्र। भारतीय किसानों के लिए ❤️ से बनाया गया।',
        # ── Hero / Home ──
        'hero_badge': '🌿 AI-आधारित फसल सुरक्षा मंच',
        'hero_title': 'स्मार्ट AI से अपनी फसल को बचाएं',
        'hero_subtitle': 'किसानमित्र 8+ फसलों में रोगों की तुरंत पहचान करता है। पत्ते की फोटो अपलोड करें, सेकंड में निदान और उपचार पाएं।',
        'hero_btn_detect': 'रोग पहचानें', 'hero_btn_library': 'रोग पुस्तकालय',
        'stat_crops': 'फसल मॉड्यूल', 'stat_predictions': 'कुल पहचान', 'stat_diseases': 'रोग शामिल',
        'home_why_label': 'क्यों किसानमित्र', 'home_why_title': 'स्मार्ट खेती, सरल तरीके से',
        'home_why_sub': 'AI और कृषि विशेषज्ञता को मिलाकर आपकी फसल की सुरक्षा करना',
        'feat1_title': 'AI-आधारित पहचान', 'feat1_desc': 'हजारों वास्तविक फसल छवियों पर प्रशिक्षित डीप लर्निंग मॉडल 5 सेकंड में सटीक रोग पहचान करते हैं।',
        'feat2_title': 'तुरंत उपचार सलाह', 'feat2_desc': 'पहचाने गए रोग के लिए कीटनाशक नाम और खुराक सहित सटीक उपचार सिफारिशें पाएं।',
        'feat3_title': '8 फसल मॉड्यूल', 'feat3_desc': 'टमाटर, आलू, मक्का, अंगूर, सेब, चावल, गेहूं और आम — प्रमुख भारतीय फसलों को कवर करता है।',
        'feat4_title': 'मौसम सलाह', 'feat4_desc': 'रोग जोखिम पूर्वानुमान से जुड़े वास्तविक मौसम डेटा। जानें कब फंगल या बैक्टीरियल प्रकोप की संभावना है।',
        'feat5_title': 'फसल कैलेंडर', 'feat5_desc': 'प्रमुख भारतीय फसलों के लिए मासिक बुआई, वृद्धि और कटाई कार्यक्रम।',
        'feat6_title': 'रोग पुस्तकालय', 'feat6_desc': '38+ फसल रोगों का व्यापक विश्वकोश — लक्षण, कारण, गंभीरता और बचाव के साथ।',
        'modules_label': 'पहचान मॉड्यूल', 'modules_title': 'अपनी फसल चुनें',
        'modules_sub': 'फसल चुनें और तुरंत AI-आधारित रोग पहचान के लिए पत्ते या फल की छवि अपलोड करें',
        'detects': 'पहचानता है', 'diseases': 'रोग', 'conditions': 'स्थितियां',
        'how_label': 'प्रक्रिया', 'how_title': 'यह कैसे काम करता है', 'how_sub': '3 सरल चरणों में अपनी फसल का निदान और उपचार करें',
        'step1_title': '1. छवि अपलोड करें', 'step1_desc': 'प्रभावित पत्ते, फल या तने की स्पष्ट तस्वीर लें और किसानमित्र पर अपलोड करें।',
        'step2_title': '2. AI विश्लेषण', 'step2_desc': 'हमारा प्रशिक्षित मॉडल छवि का विश्लेषण करता है और रोग की पहचान करता है।',
        'step3_title': '3. उपचार पाएं', 'step3_desc': 'विस्तृत उपचार सिफारिशें, निवारक उपाय और गंभीरता मूल्यांकन तुरंत प्राप्त करें।',
        'impact_label': 'प्रभाव', 'impact_title': 'हमारे आंकड़े',
        'accuracy_label': '% सटीकता (टमाटर)', 'total_pred_label': 'कुल पहचान',
        'cta_title': 'आज ही अपनी फसल की सुरक्षा शुरू करें',
        'cta_sub': 'हजारों किसानों से जुड़ें जो रोग फैलने से पहले किसानमित्र से पहचान और उपचार करते हैं।',
        'try_detection': 'अभी पहचानें', 'share_feedback': 'प्रतिक्रिया दें',
        # ── Auth ──
        'login_title': 'किसानमित्र में लॉगिन करें', 'login_email': 'ईमेल पता',
        'login_password': 'पासवर्ड', 'login_btn': 'लॉगिन करें', 'login_no_account': 'खाता नहीं है?',
        'signup_title': 'अपना खाता बनाएं', 'signup_name': 'पूरा नाम',
        'signup_email': 'ईमेल पता', 'signup_password': 'पासवर्ड',
        'signup_confirm': 'पासवर्ड की पुष्टि करें', 'signup_btn': 'खाता बनाएं',
        'signup_free_credits': 'साइन अप पर 200 मुफ्त क्रेडिट मिलेंगे!',
        'signup_has_account': 'पहले से खाता है?',
        # ── Plans ──
        'plan_free': 'मुफ्त', 'plan_basic': 'बेसिक', 'plan_pro': 'प्रो', 'plan_enterprise': 'एंटरप्राइज',
        'per_month': '/माह', 'choose_plan': 'अपना प्लान चुनें',
        # ── Detection ──
        'detect_btn': 'रोग पहचानें', 'upload_image': 'फसल की छवि अपलोड करें',
        'analyzing': 'आपकी फसल की छवि का विश्लेषण हो रहा है...',
        'result_disease': 'पहचाना गया रोग', 'result_confidence': 'विश्वसनीयता',
        'result_treatment': 'उपचार', 'result_cause': 'कारण',
        'result_symptoms': 'लक्षण', 'result_prevention': 'बचाव', 'result_severity': 'गंभीरता',
        'healthy_msg': 'आपकी फसल स्वस्थ दिख रही है! 🎉',
        'login_required': 'रोग पहचान उपयोग करने के लिए कृपया लॉगिन या साइन अप करें।',
        'login_to_predict': 'लॉगिन करें', 'signup_to_predict': 'मुफ्त साइन अप करें',
        'predict_label': 'AI पहचान', 'predict_title': '🔬 फसल रोग पहचान',
        'predict_sub': 'नीचे अपनी फसल चुनें और तुरंत AI-आधारित रोग निदान के लिए पत्ते/फल की छवि अपलोड करें',
        'predict_tip': '📷 <strong>सुझाव:</strong> सर्वोत्तम परिणाम के लिए, अच्छी रोशनी में प्रभावित क्षेत्र की स्पष्ट क्लोज-अप तस्वीर लें।',
        'step1_label': 'चरण 1', 'choose_crop_title': 'अपनी फसल चुनें',
        'choose_crop_sub': 'फसल पर होवर करें जानकारी देखने के लिए, फिर पहचान शुरू करने के लिए क्लिक करें',
        'hover_crop': 'फसल पर होवर करें', 'hover_crop_sub': 'उगाने की स्थिति और सामान्य रोग देखने के लिए',
        'crop_info': 'फसल जानकारी', 'temperature': 'तापमान', 'soil': 'मिट्टी',
        'water': 'पानी', 'season': 'मौसम', 'common_diseases': 'सामान्य रोग',
        'result_title': 'पहचान परिणाम', 'result_crop': 'फसल',
        'high_conf': 'उच्च विश्वास', 'mod_conf': 'मध्यम विश्वास', 'low_conf': 'कम विश्वास',
        'try_another': 'दूसरा प्रयास करें',
        # ── Disease Library ──
        'lib_label': 'विश्वकोश', 'lib_title': '📚 फसल रोग पुस्तकालय',
        'lib_sub': '38+ फसल रोगों का व्यापक संदर्भ — लक्षण, कारण, उपचार और बचाव',
        'all_crops': '🌿 सभी फसलें', 'pathogen_cause': 'रोगज़नक़ / कारण', 'severity_label': 'गंभीरता',
        'symptoms_label': 'लक्षण', 'treatment_prev': 'उपचार और बचाव',
        'treatment_label': 'उपचार', 'prevention_label': 'बचाव',
        'detect_this': 'इस रोग की पहचान करें',
        # ── Weather ──
        'weather_label': 'मॉड्यूल 9', 'weather_title': '🌦️ मौसम सलाह',
        'weather_sub': 'आपके क्षेत्र के लिए फसल रोग जोखिम सलाह सहित वास्तविक मौसम डेटा',
        'weather_placeholder': 'शहर दर्ज करें (जैसे पुणे, नाशिक, नागपुर)',
        'get_weather': 'मौसम देखें', 'humidity': 'आर्द्रता', 'wind': 'हवा', 'uv_index': 'UV सूचकांक',
        'disease_advisory': '🌿 फसल रोग सलाह',
        'risk_guide_title': '📊 मौसम-रोग जोखिम मार्गदर्शिका',
        'condition': 'स्थिति', 'risk_level': 'जोखिम स्तर', 'likely_disease': 'संभावित रोग',
        'action': 'कार्रवाई',
        'weather_tip_title': '🌱 फसल सलाह',
        'weather_tip1': 'जब 3+ दिनों तक आर्द्रता > 75% हो तो निवारक रूप से फफूंदनाशक का छिड़काव करें।',
        'weather_tip2': 'जब तापमान 35°C से अधिक हो तो सिंचाई की आवृत्ति बढ़ाएं।',
        'weather_tip3': 'गेहूं के मौसम में ठंडी रातों (< 15°C) के दौरान रतुआ रोगों की निगरानी करें।',
        'weather_tip4': 'जब पत्ती की नमी 6 घंटे से अधिक हो तो ऊपरी सिंचाई से बचें।',
        'adv_high_humidity': '⚠️ उच्च आर्द्रता: फफूंद रोगों का खतरा। निवारक फफूंदनाशक लगाएं।',
        'adv_high_temp': '🌡️ उच्च तापमान: संवेदनशील फसलों के लिए पर्याप्त सिंचाई और छाया सुनिश्चित करें।',
        'adv_normal': '✅ फसल वृद्धि के लिए अनुकूल मौसम की स्थिति।',
        # ── Crop Calendar ──
        'cal_label': 'मॉड्यूल 10', 'cal_title': '📅 फसल कैलेंडर',
        'cal_sub': 'प्रमुख भारतीय फसलों के लिए मासिक बुआई, उगाने और कटाई की मार्गदर्शिका',
        'cal_heading': 'भारत फसल कैलेंडर 2024',
        'cal_legend': 'B = बोएं | U = उगाएं | K = काटें | — = बंद मौसम',
        'cal_sow': 'बुआई', 'cal_grow': 'उगाना', 'cal_harvest': 'कटाई', 'cal_off': 'बंद मौसम',
        'crop_col': 'फसल',
        'kharif_title': '☀️ खरीफ मौसम (जून–अक्टूबर)',
        'kharif_desc': 'मानसून फसलें। उच्च आर्द्रता और वर्षा फफूंद रोगों के लिए अनुकूल परिस्थितियां बनाती है।',
        'kharif_r1': '🔴 उच्च जोखिम: देर से झुलसा, पत्ती फफूंद',
        'kharif_r2': '🟡 मध्यम: जीवाणु रोग',
        'kharif_r3': '💊 निवारक फफूंदनाशक लगाएं',
        'rabi_title': '❄️ रबी मौसम (नवंबर–मार्च)',
        'rabi_desc': 'शीतकालीन फसलें। ठंडी रातें कम आर्द्रता के साथ, लेकिन रतुआ और ख़र्रा चिंताजनक।',
        'rabi_r1': '🔴 उच्च जोखिम: रतुआ रोग (गेहूं)',
        'rabi_r2': '🟡 मध्यम: चूर्णिल आसिता',
        'rabi_r3': '💊 प्रोपिकोनाज़ोल की निगरानी और छिड़काव',
        # ── About ──
        'about_title': '🌱 किसानमित्र के बारे में',
        'about_sub': 'भारतीय किसानों के लिए AI-आधारित पौधे रोग पहचान — हमारा मिशन, टीम और तकनीक',
        'our_mission': 'हमारा मिशन',
        'about_mission_title': 'स्मार्ट तकनीक से किसानों को सशक्त बनाना',
        'about_p1': 'भारत हर साल फसल रोगों से 15–20% कृषि उत्पादन खोता है। किसानमित्र इसे बदलने के लिए बनाया गया है। डीप लर्निंग AI को सुलभ मोबाइल तकनीक के साथ मिलाकर, हम किसानों को तुरंत रोगों की पहचान करने और फसल नष्ट होने से पहले सटीक कार्रवाई करने में मदद करते हैं।',
        'about_p2': 'हमारा मंच 8 प्रमुख फसल प्रकारों में 38+ रोगों को कवर करता है, जो न केवल पहचान बल्कि पूर्ण उपचार मार्गदर्शन, मौसम सलाह और फसल कैलेंडर भी प्रदान करता है।',
        'try_detection_btn': 'पहचान आजमाएं', 'view_library_btn': 'पुस्तकालय देखें',
        'crops_covered': 'फसलें शामिल', 'accuracy_stat': 'सटीकता', 'built_for': 'के लिए बनाया', 'farmers': 'किसान',
        'the_team': 'टीम', 'team_title': 'परियोजना डेवलपर्स',
        'team_sub': 'अंतिम वर्ष के कंप्यूटर इंजीनियरिंग छात्र भारत के किसानों के लिए तकनीक बना रहे हैं',
        'dev1_name': 'डेवलपर 1', 'dev1_role': 'फुल स्टैक + ML इंजीनियर',
        'dev1_bio': 'मॉडल प्रशिक्षण, बैकेंड API और डेटाबेस डिज़ाइन के लिए जिम्मेदार',
        'dev2_name': 'डेवलपर 2', 'dev2_role': 'फ्रंटेंड + UI/UX डिज़ाइनर',
        'dev2_bio': 'वेब डिज़ाइन, टेम्पलेट, उपयोगकर्ता अनुभव और परीक्षण के लिए जिम्मेदार',
        'tech_label': 'तकनीक', 'tech_title': 'तकनीकी स्टैक',
        # ── Contact ──
        'contact_title': '📬 संपर्क करें',
        'contact_sub': 'प्रश्न हैं या सहायता चाहिए? हम पूरे भारत के किसानों की मदद के लिए यहां हैं',
        'send_message': 'संदेश भेजें',
        'contact_form_sub': 'नीचे फॉर्म भरें और हम 24 घंटे में जवाब देंगे',
        'full_name': 'पूरा नाम *', 'email_label': 'ईमेल *', 'phone_label': 'फोन',
        'subject_label': 'विषय', 'message_label': 'संदेश *',
        'subj_general': 'सामान्य पूछताछ', 'subj_support': 'तकनीकी सहायता',
        'subj_detection': 'रोग पहचान सहायता', 'subj_research': 'अनुसंधान सहयोग',
        'subj_bug': 'बग की रिपोर्ट करें',
        'msg_placeholder': 'अपनी समस्या बताएं...',
        'send_btn': 'संदेश भेजें',
        'get_in_touch': 'संपर्क करें', 'reach_us': 'इन माध्यमों से हम तक पहुंचें',
        'phone_hours': 'फोन (सोम–शनि, सुबह 9–शाम 6)',
        'location_label': 'स्थान', 'location_val': 'पुणे, महाराष्ट्र, भारत',
        # ── Feedback ──
        'feedback_title': '⭐ उपयोगकर्ता प्रतिक्रिया',
        'feedback_sub': 'अपना अनुभव साझा करके किसानमित्र को बेहतर बनाने में मदद करें',
        'share_feedback_title': 'अपनी प्रतिक्रिया साझा करें',
        'feedback_form_sub': 'आपका अनुभव हमें किसानों की बेहतर सेवा करने में मदद करता है',
        'your_rating': 'आपकी रेटिंग', 'your_message': 'आपका संदेश *',
        'msg_placeholder_fb': 'किसानमित्र के साथ अपना अनुभव बताएं...',
        'submit_feedback': 'प्रतिक्रिया जमा करें',
        'why_feedback': 'आपकी प्रतिक्रिया क्यों मायने रखती है',
        'fb_reason1': '🌱 मॉडल सटीकता सुधारने में मदद',
        'fb_reason2': '🤝 भविष्य के फसल मॉड्यूल को आकार देना',
        'fb_reason3': '📊 परियोजना मूल्यांकन में उपयोग',
        'fb_reason4': '🚀 मंच सुधारों को बढ़ावा देना',
        'platform_stats': 'मंच के आंकड़े',
        'satisfaction': '% संतुष्टि', 'feedbacks_count': 'प्रतिक्रियाएं',
        'community_label': 'समुदाय', 'what_farmers_say': 'किसान क्या कहते हैं',
        # ── Profile ──
        'profile_title': 'मेरी प्रोफाइल', 'total_scans': 'कुल स्कैन',
        'member_since': 'सदस्यता से', 'current_plan': 'वर्तमान प्लान',
        'scan_history': 'स्कैन इतिहास', 'no_scans': 'अभी तक कोई स्कैन नहीं',
    },
    'mr': {
        # ── Nav ──
        'nav_home': 'मुख्यपृष्ठ', 'nav_predict': 'ओळखा', 'nav_library': 'ग्रंथालय',
        'nav_weather': 'हवामान', 'nav_calendar': 'दिनदर्शिका', 'nav_about': 'आमच्याबद्दल',
        'nav_contact': 'संपर्क', 'nav_feedback': 'अभिप्राय',
        'nav_login': 'लॉगिन', 'nav_signup': 'नोंदणी', 'nav_logout': 'बाहेर पडा',
        'nav_profile': 'माझी प्रोफाइल',
        'credits_label': 'क्रेडिट', 'credits_remaining': 'उर्वरित क्रेडिट',
        'credits_used': 'वापरलेले क्रेडिट', 'each_prediction': 'प्रति ओळख 5 क्रेडिट',
        'no_credits_title': 'क्रेडिट संपले!',
        'no_credits_msg': 'आपले सर्व मोफत क्रेडिट संपले आहेत. सुरू ठेवण्यासाठी एखादी योजना खरेदी करा.',
        'upgrade_now': 'आता अपग्रेड करा',
        # ── Footer ──
        'footer_tagline': 'भारतीय शेतकऱ्यांसाठी AI-आधारित वनस्पती रोग ओळख. पिकांचे संरक्षण, उपजीविका सुरक्षित करणे.',
        'footer_resources': 'संसाधने', 'footer_plans': 'योजना आणि किंमत', 'footer_rights': '© 2024 किसानमित्र. भारतीय शेतकऱ्यांसाठी ❤️ ने बनवले.',
        # ── Hero / Home ──
        'hero_badge': '🌿 AI-आधारित पीक संरक्षण मंच',
        'hero_title': 'स्मार्ट AI ने आपल्या पिकाचे रक्षण करा',
        'hero_subtitle': 'किसानमित्र 8+ पिकांमधील रोगांची त्वरित ओळख करतो. पानाचा फोटो अपलोड करा, सेकंदात निदान आणि उपचार मिळवा.',
        'hero_btn_detect': 'रोग ओळखा', 'hero_btn_library': 'रोग ग्रंथालय',
        'stat_crops': 'पीक मॉड्यूल', 'stat_predictions': 'एकूण ओळख', 'stat_diseases': 'रोग समाविष्ट',
        'home_why_label': 'किसानमित्र का?', 'home_why_title': 'स्मार्ट शेती, सोप्या पद्धतीने',
        'home_why_sub': 'AI आणि कृषी तज्ज्ञतेला एकत्र करून आपल्या पिकाचे संरक्षण करणे',
        'feat1_title': 'AI-आधारित ओळख', 'feat1_desc': 'हजारो वास्तविक पीक प्रतिमांवर प्रशिक्षित डीप लर्निंग मॉडेल 5 सेकंदात अचूक रोग ओळख करतात.',
        'feat2_title': 'त्वरित उपचार सल्ला', 'feat2_desc': 'ओळखलेल्या रोगासाठी कीटकनाशक नावे आणि मात्रांसह अचूक उपचार शिफारसी मिळवा.',
        'feat3_title': '8 पीक मॉड्यूल', 'feat3_desc': 'टोमॅटो, बटाटा, मका, द्राक्ष, सफरचंद, तांदूळ, गहू आणि आंबा — प्रमुख भारतीय पिकांसाठी.',
        'feat4_title': 'हवामान सल्ला', 'feat4_desc': 'रोग जोखीम अंदाजाशी जोडलेला वास्तविक हवामान डेटा. बुरशीजन्य किंवा जीवाणूजन्य उद्रेकाची शक्यता जाणून घ्या.',
        'feat5_title': 'पीक दिनदर्शिका', 'feat5_desc': 'प्रमुख भारतीय पिकांसाठी मासिक पेरणी, वाढ आणि काढणी वेळापत्रक.',
        'feat6_title': 'रोग ग्रंथालय', 'feat6_desc': '38+ पीक रोगांचा सर्वसमावेशक ज्ञानकोश — लक्षणे, कारणे, तीव्रता आणि प्रतिबंध.',
        'modules_label': 'ओळख मॉड्यूल', 'modules_title': 'आपले पीक निवडा',
        'modules_sub': 'पीक निवडा आणि त्वरित AI-आधारित रोग निदानासाठी पान किंवा फळाचा फोटो अपलोड करा',
        'detects': 'ओळखते', 'diseases': 'रोग', 'conditions': 'अवस्था',
        'how_label': 'प्रक्रिया', 'how_title': 'हे कसे कार्य करते', 'how_sub': '3 सोप्या चरणांमध्ये आपल्या पिकाचे निदान आणि उपचार करा',
        'step1_title': '1. फोटो अपलोड करा', 'step1_desc': 'प्रभावित पान, फळ किंवा खोड्याचा स्पष्ट फोटो काढा आणि किसानमित्रवर अपलोड करा.',
        'step2_title': '2. AI विश्लेषण', 'step2_desc': 'आमचे प्रशिक्षित मॉडेल प्रतिमेचे विश्लेषण करते आणि रोग ओळखते.',
        'step3_title': '3. उपचार मिळवा', 'step3_desc': 'तपशीलवार उपचार शिफारसी, प्रतिबंधात्मक उपाय आणि तीव्रता मूल्यांकन त्वरित मिळवा.',
        'impact_label': 'प्रभाव', 'impact_title': 'आमचे आकडे',
        'accuracy_label': '% अचूकता (टोमॅटो)', 'total_pred_label': 'एकूण ओळख',
        'cta_title': 'आजच आपल्या पिकाचे संरक्षण सुरू करा',
        'cta_sub': 'हजारो शेतकऱ्यांसोबत जोडा जे रोग पसरण्यापूर्वी किसानमित्रने ओळखतात आणि उपचार करतात.',
        'try_detection': 'आता ओळखा', 'share_feedback': 'अभिप्राय द्या',
        # ── Auth ──
        'login_title': 'किसानमित्रमध्ये लॉगिन करा', 'login_email': 'ईमेल पत्ता',
        'login_password': 'पासवर्ड', 'login_btn': 'लॉगिन करा', 'login_no_account': 'खाते नाही?',
        'signup_title': 'आपले खाते तयार करा', 'signup_name': 'पूर्ण नाव',
        'signup_email': 'ईमेल पत्ता', 'signup_password': 'पासवर्ड',
        'signup_confirm': 'पासवर्ड पुष्टी करा', 'signup_btn': 'खाते तयार करा',
        'signup_free_credits': 'नोंदणीवर 200 मोफत क्रेडिट मिळतात!',
        'signup_has_account': 'आधीच खाते आहे?',
        # ── Plans ──
        'plan_free': 'मोफत', 'plan_basic': 'बेसिक', 'plan_pro': 'प्रो', 'plan_enterprise': 'एंटरप्राइझ',
        'per_month': '/महिना', 'choose_plan': 'आपली योजना निवडा',
        # ── Detection ──
        'detect_btn': 'रोग ओळखा', 'upload_image': 'पिकाचा फोटो अपलोड करा',
        'analyzing': 'आपल्या पिकाच्या प्रतिमेचे विश्लेषण होत आहे...',
        'result_disease': 'आढळलेला रोग', 'result_confidence': 'विश्वासार्हता',
        'result_treatment': 'उपचार', 'result_cause': 'कारण',
        'result_symptoms': 'लक्षणे', 'result_prevention': 'प्रतिबंध', 'result_severity': 'तीव्रता',
        'healthy_msg': 'आपले पीक निरोगी दिसत आहे! 🎉',
        'login_required': 'रोग ओळख वापरण्यासाठी कृपया लॉगिन किंवा नोंदणी करा.',
        'login_to_predict': 'लॉगिन करा', 'signup_to_predict': 'मोफत नोंदणी करा',
        'predict_label': 'AI ओळख', 'predict_title': '🔬 पीक रोग ओळख',
        'predict_sub': 'खाली आपले पीक निवडा आणि त्वरित AI-आधारित रोग निदानासाठी पान/फळाचा फोटो अपलोड करा',
        'predict_tip': '📷 <strong>टिप:</strong> सर्वोत्तम निकालासाठी, चांगल्या प्रकाशात प्रभावित भागाचा स्पष्ट क्लोज-अप फोटो काढा.',
        'step1_label': 'पायरी 1', 'choose_crop_title': 'आपले पीक निवडा',
        'choose_crop_sub': 'माहिती पाहण्यासाठी पिकावर होवर करा, नंतर ओळख सुरू करण्यासाठी क्लिक करा',
        'hover_crop': 'पिकावर होवर करा', 'hover_crop_sub': 'वाढीची परिस्थिती आणि सामान्य रोग पाहण्यासाठी',
        'crop_info': 'पीक माहिती', 'temperature': 'तापमान', 'soil': 'माती',
        'water': 'पाणी', 'season': 'हंगाम', 'common_diseases': 'सामान्य रोग',
        'result_title': 'ओळख निकाल', 'result_crop': 'पीक',
        'high_conf': 'उच्च विश्वास', 'mod_conf': 'मध्यम विश्वास', 'low_conf': 'कमी विश्वास',
        'try_another': 'दुसरा प्रयत्न करा',
        # ── Disease Library ──
        'lib_label': 'ज्ञानकोश', 'lib_title': '📚 पीक रोग ग्रंथालय',
        'lib_sub': '38+ पीक रोगांचा सर्वसमावेशक संदर्भ — लक्षणे, कारणे, उपचार आणि प्रतिबंध',
        'all_crops': '🌿 सर्व पिके', 'pathogen_cause': 'रोगकारक / कारण', 'severity_label': 'तीव्रता',
        'symptoms_label': 'लक्षणे', 'treatment_prev': 'उपचार आणि प्रतिबंध',
        'treatment_label': 'उपचार', 'prevention_label': 'प्रतिबंध',
        'detect_this': 'हा रोग ओळखा',
        # ── Weather ──
        'weather_label': 'मॉड्यूल 9', 'weather_title': '🌦️ हवामान सल्ला',
        'weather_sub': 'आपल्या प्रदेशासाठी पीक रोग जोखीम सल्ल्यासह वास्तविक हवामान डेटा',
        'weather_placeholder': 'शहर प्रविष्ट करा (उदा. पुणे, नाशिक, नागपूर)',
        'get_weather': 'हवामान पाहा', 'humidity': 'आर्द्रता', 'wind': 'वारा', 'uv_index': 'UV निर्देशांक',
        'disease_advisory': '🌿 पीक रोग सल्ला',
        'risk_guide_title': '📊 हवामान-रोग जोखीम मार्गदर्शिका',
        'condition': 'परिस्थिती', 'risk_level': 'जोखीम पातळी', 'likely_disease': 'संभाव्य रोग',
        'action': 'कृती',
        'weather_tip_title': '🌱 पीक सल्ला',
        'weather_tip1': '3+ दिवस आर्द्रता > 75% असेल तेव्हा प्रतिबंधात्मकपणे बुरशीनाशक फवारा.',
        'weather_tip2': 'तापमान 35°C पेक्षा जास्त असेल तेव्हा सिंचन वारंवारता वाढवा.',
        'weather_tip3': 'गहू हंगामात थंड रात्री (< 15°C) दरम्यान गंज रोगांवर लक्ष ठेवा.',
        'weather_tip4': 'पानाची ओलसरपणा 6 तासांपेक्षा जास्त असेल तेव्हा वरून सिंचन टाळा.',
        'adv_high_humidity': '⚠️ उच्च आर्द्रता: बुरशीजन्य रोगांचा धोका. प्रतिबंधात्मक बुरशीनाशक लावा.',
        'adv_high_temp': '🌡️ उच्च तापमान: संवेदनशील पिकांसाठी पुरेसे सिंचन आणि सावली सुनिश्चित करा.',
        'adv_normal': '✅ पीक वाढीसाठी अनुकूल हवामान परिस्थिती.',
        # ── Crop Calendar ──
        'cal_label': 'मॉड्यूल 10', 'cal_title': '📅 पीक दिनदर्शिका',
        'cal_sub': 'प्रमुख भारतीय पिकांसाठी मासिक पेरणी, वाढ आणि काढणी मार्गदर्शिका',
        'cal_heading': 'भारत पीक दिनदर्शिका 2024',
        'cal_legend': 'P = पेरा | V = वाढवा | K = काढा | — = बंद हंगाम',
        'cal_sow': 'पेरणी', 'cal_grow': 'वाढ', 'cal_harvest': 'काढणी', 'cal_off': 'बंद हंगाम',
        'crop_col': 'पीक',
        'kharif_title': '☀️ खरीप हंगाम (जून–ऑक्टोबर)',
        'kharif_desc': 'मान्सून पिके. उच्च आर्द्रता आणि पाऊस बुरशीजन्य रोगांसाठी आदर्श परिस्थिती निर्माण करतात.',
        'kharif_r1': '🔴 उच्च जोखीम: उशिरा करपा, पर्ण बुरशी',
        'kharif_r2': '🟡 मध्यम: जीवाणूजन्य रोग',
        'kharif_r3': '💊 प्रतिबंधात्मक बुरशीनाशक लावा',
        'rabi_title': '❄️ रबी हंगाम (नोव्हेंबर–मार्च)',
        'rabi_desc': 'हिवाळी पिके. थंड रात्री कमी आर्द्रतेसह, परंतु गंज आणि भुरी चिंताजनक.',
        'rabi_r1': '🔴 उच्च जोखीम: गंज रोग (गहू)',
        'rabi_r2': '🟡 मध्यम: भुरी',
        'rabi_r3': '💊 प्रोपिकोनाझोल फवारणी करा',
        # ── About ──
        'about_title': '🌱 किसानमित्रबद्दल',
        'about_sub': 'भारतीय शेतकऱ्यांसाठी AI-आधारित वनस्पती रोग ओळख — आमचे ध्येय, टीम आणि तंत्रज्ञान',
        'our_mission': 'आमचे ध्येय',
        'about_mission_title': 'स्मार्ट तंत्रज्ञानाने शेतकऱ्यांना सक्षम करणे',
        'about_p1': 'भारत दरवर्षी पीक रोगांमुळे 15–20% कृषी उत्पादन गमावतो. किसानमित्र हे बदलण्यासाठी बनवले आहे. डीप लर्निंग AI ला सुलभ मोबाइल तंत्रज्ञानाशी जोडून, आम्ही शेतकऱ्यांना त्वरित रोग ओळखण्यास आणि पीक नष्ट होण्यापूर्वी अचूक कृती करण्यास मदत करतो.',
        'about_p2': 'आमचा मंच 8 प्रमुख पीक प्रकारांमध्ये 38+ रोग समाविष्ट करतो, केवळ ओळखच नाही तर संपूर्ण उपचार मार्गदर्शन, हवामान सल्ला आणि पीक दिनदर्शिका देतो.',
        'try_detection_btn': 'ओळख वापरून पाहा', 'view_library_btn': 'ग्रंथालय पाहा',
        'crops_covered': 'पिके समाविष्ट', 'accuracy_stat': 'अचूकता', 'built_for': 'साठी बनवले', 'farmers': 'शेतकरी',
        'the_team': 'टीम', 'team_title': 'प्रकल्प विकासक',
        'team_sub': 'अंतिम वर्षाचे संगणक अभियांत्रिकी विद्यार्थी भारताच्या शेतकऱ्यांसाठी तंत्रज्ञान बनवत आहेत',
        'dev1_name': 'विकासक 1', 'dev1_role': 'फुल स्टॅक + ML अभियंता',
        'dev1_bio': 'मॉडेल प्रशिक्षण, बॅकएंड API आणि डेटाबेस डिझाइनसाठी जबाबदार',
        'dev2_name': 'विकासक 2', 'dev2_role': 'फ्रंटएंड + UI/UX डिझायनर',
        'dev2_bio': 'वेब डिझाइन, टेम्पलेट, वापरकर्ता अनुभव आणि चाचणीसाठी जबाबदार',
        'tech_label': 'तंत्रज्ञान', 'tech_title': 'तांत्रिक स्टॅक',
        # ── Contact ──
        'contact_title': '📬 संपर्क करा',
        'contact_sub': 'प्रश्न आहेत किंवा मदत हवी आहे? आम्ही संपूर्ण भारतातील शेतकऱ्यांना मदत करण्यासाठी येथे आहोत',
        'send_message': 'संदेश पाठवा',
        'contact_form_sub': 'खाली फॉर्म भरा आणि आम्ही 24 तासांत उत्तर देऊ',
        'full_name': 'पूर्ण नाव *', 'email_label': 'ईमेल *', 'phone_label': 'फोन',
        'subject_label': 'विषय', 'message_label': 'संदेश *',
        'subj_general': 'सामान्य चौकशी', 'subj_support': 'तांत्रिक सहाय्य',
        'subj_detection': 'रोग ओळख मदत', 'subj_research': 'संशोधन सहयोग',
        'subj_bug': 'बग अहवाल द्या',
        'msg_placeholder': 'आपली समस्या सांगा...',
        'send_btn': 'संदेश पाठवा',
        'get_in_touch': 'संपर्क करा', 'reach_us': 'या माध्यमांद्वारे आमच्यापर्यंत पोहोचा',
        'phone_hours': 'फोन (सोम–शनि, सकाळी 9–सायंकाळी 6)',
        'location_label': 'स्थान', 'location_val': 'पुणे, महाराष्ट्र, भारत',
        # ── Feedback ──
        'feedback_title': '⭐ वापरकर्ता अभिप्राय',
        'feedback_sub': 'आपला अनुभव सामायिक करून किसानमित्र सुधारण्यास मदत करा',
        'share_feedback_title': 'आपला अभिप्राय सामायिक करा',
        'feedback_form_sub': 'आपला अनुभव आम्हाला शेतकऱ्यांची अधिक चांगली सेवा करण्यास मदत करतो',
        'your_rating': 'आपचे मूल्यांकन', 'your_message': 'आपला संदेश *',
        'msg_placeholder_fb': 'किसानमित्रसोबतचा आपला अनुभव सांगा...',
        'submit_feedback': 'अभिप्राय सादर करा',
        'why_feedback': 'आपला अभिप्राय का महत्त्वाचा आहे',
        'fb_reason1': '🌱 मॉडेल अचूकता सुधारण्यास मदत',
        'fb_reason2': '🤝 भविष्यातील पीक मॉड्यूल घडवणे',
        'fb_reason3': '📊 प्रकल्प मूल्यांकनात वापर',
        'fb_reason4': '🚀 मंच सुधारणांना चालना देणे',
        'platform_stats': 'मंच आकडेवारी',
        'satisfaction': '% समाधान', 'feedbacks_count': 'अभिप्राय',
        'community_label': 'समुदाय', 'what_farmers_say': 'शेतकरी काय म्हणतात',
        # ── Profile ──
        'profile_title': 'माझी प्रोफाइल', 'total_scans': 'एकूण स्कॅन',
        'member_since': 'सदस्यत्व पासून', 'current_plan': 'सध्याची योजना',
        'scan_history': 'स्कॅन इतिहास', 'no_scans': 'अजून कोणतेही स्कॅन नाही',
    }
}

PLANS = [
    {
        'id': 'basic',
        'name_key': 'plan_basic',
        'price': 99,
        'credits': 500,
        'features': {
            'en': ['500 Credits/month', '5 Credits per scan', 'All 8 crop modules', 'Email support'],
            'hi': ['500 क्रेडिट/माह', 'प्रति स्कैन 5 क्रेडिट', 'सभी 8 फसल मॉड्यूल', 'ईमेल सहायता'],
            'mr': ['500 क्रेडिट/महिना', 'प्रति स्कॅन 5 क्रेडिट', 'सर्व 8 पीक मॉड्यूल', 'ईमेल सहाय्य'],
        },
        'popular': False, 'color': '#22c55e'
    },
    {
        'id': 'pro',
        'name_key': 'plan_pro',
        'price': 249,
        'credits': 1500,
        'features': {
            'en': ['1500 Credits/month', '5 Credits per scan', 'Priority support', 'Crop calendar access', 'Weather alerts'],
            'hi': ['1500 क्रेडिट/माह', 'प्रति स्कैन 5 क्रेडिट', 'प्राथमिकता सहायता', 'फसल कैलेंडर', 'मौसम अलर्ट'],
            'mr': ['1500 क्रेडिट/महिना', 'प्रति स्कॅन 5 क्रेडिट', 'प्राधान्य सहाय्य', 'पीक दिनदर्शिका', 'हवामान अलर्ट'],
        },
        'popular': True, 'color': '#16a34a'
    },
    {
        'id': 'enterprise',
        'name_key': 'plan_enterprise',
        'price': 699,
        'credits': 5000,
        'features': {
            'en': ['5000 Credits/month', '5 Credits per scan', 'Dedicated support', 'API access', 'Multi-farm management', 'Custom reports'],
            'hi': ['5000 क्रेडिट/माह', 'प्रति स्कैन 5 क्रेडिट', 'समर्पित सहायता', 'API एक्सेस', 'बहु-खेत प्रबंधन', 'कस्टम रिपोर्ट'],
            'mr': ['5000 क्रेडिट/महिना', 'प्रति स्कॅन 5 क्रेडिट', 'समर्पित सहाय्य', 'API प्रवेश', 'बहु-शेत व्यवस्थापन', 'सानुकूल अहवाल'],
        },
        'popular': False, 'color': '#15803d'
    },
]

def get_lang():
    return session.get('lang', 'en')

def t(key):
    lang = get_lang()
    return TRANSLATIONS.get(lang, TRANSLATIONS['en']).get(key, TRANSLATIONS['en'].get(key, key))

app.jinja_env.globals['t'] = t
app.jinja_env.globals['get_lang'] = get_lang
app.jinja_env.globals['is_admin_user'] = is_admin_user

# ── Disease Data ──────────────────────────────────────────────────────────────
DISEASE_DATA = {
    "tomato": {
        "name": "Tomato", "icon": "🍅",
        "classes": ["Bacterial Spot","Early Blight","Late Blight","Leaf Mold","Septoria Leaf Spot","Spider Mites","Target Spot","Tomato Yellow Leaf Curl Virus","Tomato Mosaic Virus","Healthy"],
        "treatments": {
            "Bacterial Spot": {"cause":"Xanthomonas campestris bacteria","symptoms":"Small, dark, water-soaked spots on leaves and fruits","treatment":"Apply copper-based bactericides. Remove infected plant parts. Ensure proper spacing.","prevention":"Use disease-free seeds, crop rotation, avoid overhead irrigation","severity":"High"},
            "Early Blight": {"cause":"Alternaria solani fungus","symptoms":"Dark concentric rings forming bull's-eye pattern on older leaves","treatment":"Apply fungicides like Mancozeb or Chlorothalonil. Remove affected leaves.","prevention":"Crop rotation, mulching, avoid wetting foliage","severity":"Medium"},
            "Late Blight": {"cause":"Phytophthora infestans","symptoms":"Pale green water-soaked spots turning dark brown on leaves","treatment":"Apply Metalaxyl or Cymoxanil fungicide immediately. Destroy infected plants.","prevention":"Resistant varieties, proper ventilation, avoid overhead watering","severity":"Critical"},
            "Leaf Mold": {"cause":"Passalora fulva fungus","symptoms":"Pale green to yellow spots on upper leaf surface with olive mold below","treatment":"Improve ventilation, apply fungicide (Chlorothalonil). Remove affected leaves.","prevention":"Reduce humidity, proper spacing, resistant varieties","severity":"Medium"},
            "Septoria Leaf Spot": {"cause":"Septoria lycopersici","symptoms":"Small circular spots with dark borders and light centers","treatment":"Apply Mancozeb or Copper fungicide. Remove infected lower leaves.","prevention":"Crop rotation, mulch to prevent soil splash","severity":"Medium"},
            "Spider Mites": {"cause":"Tetranychus urticae (pest)","symptoms":"Tiny yellow or white speckling on leaves, fine webbing underneath","treatment":"Apply miticide or insecticidal soap. Spray forceful water to dislodge mites.","prevention":"Maintain humidity, avoid dusty conditions, introduce predatory mites","severity":"Medium"},
            "Target Spot": {"cause":"Corynespora cassiicola fungus","symptoms":"Circular lesions with concentric rings resembling a target","treatment":"Apply Azoxystrobin or Boscalid fungicide. Remove infected tissue.","prevention":"Good air circulation, avoid leaf wetness","severity":"Medium"},
            "Tomato Yellow Leaf Curl Virus": {"cause":"TYLCV (transmitted by whiteflies)","symptoms":"Upward curling of leaves, yellowing, stunted growth","treatment":"No cure. Remove infected plants. Control whitefly vector with insecticides.","prevention":"Resistant varieties, control whiteflies, reflective mulches","severity":"Critical"},
            "Tomato Mosaic Virus": {"cause":"Tomato Mosaic Virus (ToMV)","symptoms":"Mosaic pattern of light and dark green on leaves, distortion","treatment":"No chemical cure. Remove and destroy infected plants.","prevention":"Use certified disease-free seeds, disinfect tools, control aphids","severity":"High"},
            "Healthy": {"cause":"N/A","symptoms":"Plant appears healthy with no visible disease symptoms","treatment":"Continue regular care and monitoring","prevention":"Maintain good agricultural practices","severity":"None"}
        }
    },
    "potato": {
        "name": "Potato", "icon": "🥔",
        "classes": ["Early Blight","Late Blight","Healthy"],
        "treatments": {
            "Early Blight": {"cause":"Alternaria solani","symptoms":"Brown spots with concentric rings on lower/older leaves","treatment":"Apply Mancozeb (2g/L water). Remove infected leaves.","prevention":"Certified seed, crop rotation, balanced fertilization","severity":"Medium"},
            "Late Blight": {"cause":"Phytophthora infestans","symptoms":"Water-soaked lesions turning dark brown/black rapidly","treatment":"Apply Metalaxyl + Mancozeb immediately. Destroy infected crop.","prevention":"Certified seed tubers, destroy volunteer plants, good drainage","severity":"Critical"},
            "Healthy": {"cause":"N/A","symptoms":"No symptoms, plant is healthy","treatment":"No treatment needed","prevention":"Continue regular crop monitoring","severity":"None"}
        }
    },
    "corn": {
        "name": "Corn / Maize", "icon": "🌽",
        "classes": ["Cercospora Leaf Spot","Common Rust","Northern Leaf Blight","Healthy"],
        "treatments": {
            "Cercospora Leaf Spot": {"cause":"Cercospora zeae-maydis","symptoms":"Rectangular gray lesions with brown borders, parallel to leaf veins","treatment":"Apply foliar fungicide (Trifloxystrobin). Ensure good air circulation.","prevention":"Resistant hybrids, crop rotation, reduce crop debris","severity":"Medium"},
            "Common Rust": {"cause":"Puccinia sorghi","symptoms":"Small, circular to elongated orange/brown pustules on both leaf surfaces","treatment":"Apply fungicide (Propiconazole) at early stage.","prevention":"Resistant varieties, early planting, crop rotation","severity":"Medium"},
            "Northern Leaf Blight": {"cause":"Setosphaeria turcica","symptoms":"Long, elliptical grayish-green lesions (1-6 inches)","treatment":"Apply Mancozeb or Azoxystrobin at first sign. Reduce leaf wetness.","prevention":"Resistant hybrids, tillage to reduce debris, crop rotation","severity":"High"},
            "Healthy": {"cause":"N/A","symptoms":"No visible disease symptoms","treatment":"No treatment needed","prevention":"Continue monitoring and good practices","severity":"None"}
        }
    },
    "grape": {
        "name": "Grape", "icon": "🍇",
        "classes": ["Black Rot","Esca (Black Measles)","Leaf Blight","Healthy"],
        "treatments": {
            "Black Rot": {"cause":"Guignardia bidwellii","symptoms":"Brown leaf spots, shriveled black berries (mummies)","treatment":"Apply Myclobutanil or Mancozeb. Remove mummified berries.","prevention":"Remove mummies, prune for air circulation, apply protective fungicides","severity":"High"},
            "Esca (Black Measles)": {"cause":"Multiple fungal pathogens","symptoms":"Interveinal chlorosis/necrosis, tiger-stripe pattern, shriveled berries","treatment":"No effective cure. Remove and destroy infected wood.","prevention":"Protect pruning wounds with fungicide paste, use disease-free planting material","severity":"Critical"},
            "Leaf Blight": {"cause":"Pseudocercospora vitis","symptoms":"Irregular dark spots with yellow halos on leaves","treatment":"Apply copper-based fungicide or Mancozeb.","prevention":"Improve canopy management, reduce humidity","severity":"Medium"},
            "Healthy": {"cause":"N/A","symptoms":"Plant is healthy","treatment":"No treatment needed","prevention":"Regular monitoring","severity":"None"}
        }
    },
    "apple": {
        "name": "Apple", "icon": "🍎",
        "classes": ["Apple Scab","Black Rot","Cedar Apple Rust","Healthy"],
        "treatments": {
            "Apple Scab": {"cause":"Venturia inaequalis","symptoms":"Olive-green to brown velvety spots on leaves and fruit","treatment":"Apply Captan or Myclobutanil fungicide. Remove fallen leaves.","prevention":"Resistant varieties, sanitation, protective fungicide sprays","severity":"High"},
            "Black Rot": {"cause":"Botryosphaeria obtusa","symptoms":"Purple spots on leaves, rotting fruit with concentric rings","treatment":"Prune infected branches. Apply Captan or Thiophanate-methyl.","prevention":"Remove dead wood, mummified fruit, and infected bark","severity":"High"},
            "Cedar Apple Rust": {"cause":"Gymnosporangium juniperi-virginianae","symptoms":"Bright orange-yellow spots on leaves, tube-like growths underneath","treatment":"Apply Myclobutanil or Propiconazole during spring bloom.","prevention":"Remove nearby cedar/juniper trees, resistant varieties","severity":"Medium"},
            "Healthy": {"cause":"N/A","symptoms":"No disease symptoms","treatment":"No treatment needed","prevention":"Regular monitoring and good orchard hygiene","severity":"None"}
        }
    },
    "rice": {
        "name": "Rice", "icon": "🌾",
        "classes": ["Bacterial Leaf Blight","Brown Spot","Leaf Smut","Healthy"],
        "treatments": {
            "Bacterial Leaf Blight": {"cause":"Xanthomonas oryzae pv. oryzae","symptoms":"Water-soaked to yellowish stripe on leaf margins turning white/gray","treatment":"Apply Copper oxychloride or Streptomycin. Drain flooded fields.","prevention":"Resistant varieties, balanced nitrogen, avoid flooding","severity":"Critical"},
            "Brown Spot": {"cause":"Cochliobolus miyabeanus","symptoms":"Oval brown lesions with yellow halo on leaves and grains","treatment":"Apply Mancozeb or Propiconazole. Improve soil nutrition.","prevention":"Use certified seed, balanced fertilization, proper water management","severity":"High"},
            "Leaf Smut": {"cause":"Entyloma oryzae","symptoms":"Small, angular, slightly raised black spots on leaves","treatment":"Apply systemic fungicide. Remove heavily infected plant parts.","prevention":"Use healthy seeds, crop rotation","severity":"Low"},
            "Healthy": {"cause":"N/A","symptoms":"No disease symptoms","treatment":"No treatment needed","prevention":"Continue good water and nutrient management","severity":"None"}
        }
    },
    "wheat": {
        "name": "Wheat", "icon": "🌾",
        "classes": ["Leaf Rust","Stem Rust","Yellow Rust (Stripe Rust)","Powdery Mildew","Healthy"],
        "treatments": {
            "Leaf Rust": {"cause":"Puccinia triticina","symptoms":"Round to oval orange-brown pustules scattered on leaves","treatment":"Apply Propiconazole or Tebuconazole. Early application gives best results.","prevention":"Resistant varieties, early sowing, crop rotation","severity":"High"},
            "Stem Rust": {"cause":"Puccinia graminis","symptoms":"Reddish-brown pustules on stems and leaves, lodging of plants","treatment":"Apply Triadimefon or Propiconazole at flag leaf stage.","prevention":"Resistant cultivars, early planting, eradicate Barberry host","severity":"Critical"},
            "Yellow Rust (Stripe Rust)": {"cause":"Puccinia striiformis","symptoms":"Yellow pustules arranged in stripes along leaf veins","treatment":"Apply Propiconazole or Azoxystrobin at first signs.","prevention":"Resistant varieties, early sowing, seed treatment","severity":"High"},
            "Powdery Mildew": {"cause":"Blumeria graminis","symptoms":"White powdery growth on leaves and stems","treatment":"Apply Triadimefon or Sulphur-based fungicide.","prevention":"Resistant varieties, avoid excessive nitrogen, proper spacing","severity":"Medium"},
            "Healthy": {"cause":"N/A","symptoms":"No disease detected","treatment":"No treatment needed","prevention":"Continue good agronomic practices","severity":"None"}
        }
    },
    "mango": {
        "name": "Mango", "icon": "🥭",
        "classes": ["Anthracnose","Powdery Mildew","Bacterial Black Spot","Healthy"],
        "treatments": {
            "Anthracnose": {"cause":"Colletotrichum gloeosporioides","symptoms":"Black sunken lesions on fruit, dark spots on leaves and flowers","treatment":"Apply Carbendazim or Mancozeb. Spray during flowering.","prevention":"Remove infected debris, avoid wounding fruit, pre-harvest fungicide","severity":"High"},
            "Powdery Mildew": {"cause":"Oidium mangiferae","symptoms":"White powdery growth on young leaves, panicles, and fruit","treatment":"Apply Wettable Sulphur (2g/L) or Hexaconazole.","prevention":"Avoid overcrowding, monitor during cool humid weather","severity":"High"},
            "Bacterial Black Spot": {"cause":"Xanthomonas campestris pv. mangiferaeindicae","symptoms":"Angular black spots on leaves, raised lesions with yellow halo on fruit","treatment":"Apply copper-based bactericide. Prune infected branches.","prevention":"Resistant varieties, minimize mechanical damage","severity":"Medium"},
            "Healthy": {"cause":"N/A","symptoms":"No disease symptoms","treatment":"No treatment needed","prevention":"Regular monitoring and orchard sanitation","severity":"None"}
        }
    }
}

def mock_predict(module, image_bytes):
    import random
    classes = DISEASE_DATA[module]["classes"]
    predicted_class = random.choice(classes)
    confidence = round(random.uniform(0.72, 0.99), 4)
    return predicted_class, confidence

# ── Auth Routes ───────────────────────────────────────────────────────────────
@app.route('/set-lang/<lang>')
def set_lang(lang):
    if lang in ['en', 'hi', 'mr']:
        session['lang'] = lang
    return redirect(request.referrer or url_for('home'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if get_current_user():
        return redirect(url_for('home'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE email=? AND password_hash=?',
                          (email, hash_password(password))).fetchone()
        db.close()
        if user:
            session['user_id'] = user['id']
            flash('Welcome back, ' + user['name'] + '! 🌱', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password.', 'error')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if get_current_user():
        return redirect(url_for('home'))
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        if not name or not email or not password:
            flash('All fields are required.', 'error')
        elif password != confirm:
            flash('Passwords do not match.', 'error')
        elif len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
        else:
            try:
                db = get_db()
                db.execute('INSERT INTO users (name, email, password_hash, credits) VALUES (?,?,?,?)',
                           (name, email, hash_password(password), FREE_CREDITS))
                db.commit()
                user = db.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
                db.close()
                session['user_id'] = user['id']
                flash(f'Welcome to KisanMitra, {name}! You have {FREE_CREDITS} free credits. 🎉', 'success')
                return redirect(url_for('home'))
            except sqlite3.IntegrityError:
                flash('Email already registered. Please login.', 'error')
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/profile')
def profile():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    db = get_db()
    total_scans = db.execute('SELECT COUNT(*) FROM predictions WHERE user_id=?', (user['id'],)).fetchone()[0]
    recent = db.execute('SELECT * FROM predictions WHERE user_id=? ORDER BY created_at DESC LIMIT 10', (user['id'],)).fetchall()
    db.close()
    return render_template('profile.html', user=user, total_scans=total_scans, recent=recent,
                           credits_used=FREE_CREDITS - user['credits'], free_credits=FREE_CREDITS)

@app.route('/plans')
def plans():
    return render_template('plans.html', plans=PLANS, translations=TRANSLATIONS, user=get_current_user())

@app.route('/upload-profile-photo', methods=['POST'])
def upload_profile_photo():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    file = request.files.get('photo')
    if not file or file.filename == '':
        flash('No file selected.', 'error')
        return redirect(url_for('profile'))
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
        flash('Only image files are allowed (jpg, png, gif, webp).', 'error')
        return redirect(url_for('profile'))
    filename = f"profile_{user['id']}{ext}"
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(save_path)
    db = get_db()
    db.execute("UPDATE users SET profile_photo=? WHERE id=?", (filename, user['id']))
    db.commit()
    db.close()
    flash('Profile photo updated!', 'success')
    return redirect(url_for('profile'))

@app.route('/buy-plan/<plan_id>')
def buy_plan(plan_id):
    user = get_current_user()
    if not user:
        flash('Please login to purchase a plan.', 'error')
        return redirect(url_for('login'))
    plan = next((p for p in PLANS if p['id'] == plan_id), None)
    if not plan:
        flash('Invalid plan.', 'error')
        return redirect(url_for('plans'))
    db = get_db()
    db.execute('UPDATE users SET plan=?, credits=credits+? WHERE id=?',
               (plan_id, plan['credits'], user['id']))
    db.commit()
    db.close()
    lang = get_lang()
    flash(f"Plan activated! {plan['credits']} credits added. 🎉", 'success')

    # Send plan purchase confirmation email (non-blocking)
    user = get_current_user()
    email_plan_purchased(user, plan)

    return redirect(url_for('profile'))

# ── Main Routes ───────────────────────────────────────────────────────────────
@app.route('/')
def home():
    stats = {}
    try:
        db = get_db()
        stats['total_predictions'] = db.execute('SELECT COUNT(*) FROM predictions').fetchone()[0]
        stats['total_feedback'] = db.execute('SELECT COUNT(*) FROM feedback').fetchone()[0]
        db.close()
    except:
        stats = {'total_predictions': 1240, 'total_feedback': 89}
    user = get_current_user()
    return render_template('home.html', stats=stats, disease_data=DISEASE_DATA, user=user)

@app.route('/predict')
def predict_home():
    user = get_current_user()
    return render_template('predict.html', disease_data=DISEASE_DATA, user=user)

@app.route('/predict/<module>', methods=['GET', 'POST'])
def predict_module(module):
    if module not in DISEASE_DATA:
        flash('Invalid module selected', 'error')
        return redirect(url_for('predict_home'))

    user = get_current_user()
    result = None
    credit_error = False

    if request.method == 'POST':
        if not user:
            flash(t('login_required'), 'error')
            return redirect(url_for('login'))

        if user['credits'] < CREDITS_PER_PREDICTION:
            credit_error = True
        else:
            if 'image' not in request.files:
                flash('No image uploaded', 'error')
                return redirect(request.url)
            file = request.files['image']
            if file.filename == '':
                flash('No file selected', 'error')
                return redirect(request.url)
            try:
                img_bytes = file.read()
                img = Image.open(io.BytesIO(img_bytes))
                img_b64 = base64.b64encode(img_bytes).decode('utf-8')
                ext = file.filename.rsplit('.', 1)[-1].lower()
                mime = 'image/jpeg' if ext in ['jpg','jpeg'] else f'image/{ext}'

                disease, confidence = mock_predict(module, img_bytes)
                treatment = DISEASE_DATA[module]["treatments"].get(disease, {})

                img_path = f"uploads/{module}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}"
                full_path = os.path.join('static', img_path)
                with open(full_path, 'wb') as f:
                    f.write(img_bytes)

                db = get_db()
                db.execute('INSERT INTO predictions (user_id, module, disease, confidence, image_path) VALUES (?,?,?,?,?)',
                           (user['id'], module, disease, confidence, img_path))
                db.execute('UPDATE users SET credits=credits-? WHERE id=?', (CREDITS_PER_PREDICTION, user['id']))
                db.commit()
                db.close()

                # Refresh user credits
                user = get_current_user()

                result = {
                    'disease': disease,
                    'confidence': round(confidence * 100, 2),
                    'treatment': treatment,
                    'image_b64': img_b64,
                    'mime': mime,
                    'is_healthy': disease.lower() == 'healthy',
                    'severity': treatment.get('severity', 'Unknown')
                }

                # Send prediction report email (non-blocking)
                email_prediction_report(user, module, result)
            except Exception as e:
                flash(f'Error processing image: {str(e)}', 'error')

    return render_template('predict_module.html',
                           module=module,
                           module_data=DISEASE_DATA[module],
                           disease_data=DISEASE_DATA,
                           result=result,
                           user=user,
                           credit_error=credit_error,
                           credits_per_prediction=CREDITS_PER_PREDICTION,
                           plans=PLANS)

@app.route('/disease-library')
def disease_library():
    return render_template('disease_library.html', disease_data=DISEASE_DATA, user=get_current_user())

@app.route('/weather')
def weather():
    return render_template('weather.html', user=get_current_user())

@app.route('/crop-calendar')
def crop_calendar():
    return render_template('crop_calendar.html', user=get_current_user())

@app.route('/about')
def about():
    return render_template('about.html', user=get_current_user())

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone', '')
        subject = request.form.get('subject', '')
        message = request.form.get('message')
        try:
            db = get_db()
            db.execute('INSERT INTO contact (name, email, phone, subject, message) VALUES (?,?,?,?,?)',
                       (name, email, phone, subject, message))
            db.commit()
            db.close()
            flash('Thank you! Your message has been sent successfully.', 'success')
        except:
            flash('Error sending message. Please try again.', 'error')
        return redirect(url_for('contact'))
    return render_template('contact.html', user=get_current_user())

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        rating = request.form.get('rating', 5)
        try:
            db = get_db()
            db.execute('INSERT INTO feedback (name, email, message, rating) VALUES (?,?,?,?)',
                       (name, email, message, rating))
            db.commit()
            db.close()
            flash('Thank you for your feedback! 🙏', 'success')
        except:
            flash('Error submitting feedback.', 'error')
        return redirect(url_for('feedback'))
    feedbacks = []
    try:
        db = get_db()
        feedbacks = db.execute('SELECT * FROM feedback ORDER BY created_at DESC LIMIT 20').fetchall()
        db.close()
    except:
        pass
    return render_template('feedback.html', feedbacks=feedbacks, user=get_current_user())

@app.route('/api/stats')
def api_stats():
    try:
        db = get_db()
        total = db.execute('SELECT COUNT(*) as c FROM predictions').fetchone()['c']
        by_module = db.execute('SELECT module, COUNT(*) as c FROM predictions GROUP BY module').fetchall()
        db.close()
        return jsonify({'total': total, 'by_module': {row['module']: row['c'] for row in by_module}})
    except:
        return jsonify({'total': 0, 'by_module': {}})

# ── Admin Routes ─────────────────────────────────────────────────────────────

@app.route('/admin')
def admin_dashboard():
    user = get_current_user()
    if not require_admin(user):
        flash(t('admin_no_access'), 'error')
        return redirect(url_for('home'))
    db = get_db()
    total_users      = db.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    total_scans      = db.execute('SELECT COUNT(*) FROM predictions').fetchone()[0]
    total_feedback   = db.execute('SELECT COUNT(*) FROM feedback').fetchone()[0]
    total_contacts   = db.execute('SELECT COUNT(*) FROM contact').fetchone()[0]
    recent_users     = db.execute('SELECT * FROM users ORDER BY created_at DESC LIMIT 8').fetchall()
    recent_preds     = db.execute(
        "SELECT p.*, u.name as user_name FROM predictions p "
        "LEFT JOIN users u ON p.user_id=u.id ORDER BY p.created_at DESC LIMIT 10"
    ).fetchall()
    db.close()
    stats = {
        'total_users': total_users, 'total_scans': total_scans,
        'total_feedback': total_feedback, 'total_contacts': total_contacts,
    }
    return render_template('admin_dashboard.html', user=user, stats=stats,
                           recent_users=recent_users, recent_preds=recent_preds)

@app.route('/admin/users')
def admin_users():
    user = get_current_user()
    if not require_admin(user):
        flash(t('admin_no_access'), 'error')
        return redirect(url_for('home'))
    db = get_db()
    search = request.args.get('q', '').strip()
    if search:
        users = db.execute(
            "SELECT u.*, (SELECT COUNT(*) FROM predictions WHERE user_id=u.id) as scan_count "
            "FROM users u WHERE u.name LIKE ? OR u.email LIKE ? ORDER BY u.created_at DESC",
            (f'%{search}%', f'%{search}%')
        ).fetchall()
    else:
        users = db.execute(
            "SELECT u.*, (SELECT COUNT(*) FROM predictions WHERE user_id=u.id) as scan_count "
            "FROM users u ORDER BY u.created_at DESC"
        ).fetchall()
    db.close()
    return render_template('admin_users.html', user=user, users=users, search=search)

@app.route('/admin/feedback')
def admin_feedback():
    user = get_current_user()
    if not require_admin(user):
        flash(t('admin_no_access'), 'error')
        return redirect(url_for('home'))
    db = get_db()
    feedbacks = db.execute('SELECT * FROM feedback ORDER BY created_at DESC').fetchall()
    db.close()
    return render_template('admin_feedback.html', user=user, feedbacks=feedbacks)

@app.route('/admin/contacts')
def admin_contacts():
    user = get_current_user()
    if not require_admin(user):
        flash(t('admin_no_access'), 'error')
        return redirect(url_for('home'))
    db = get_db()
    contacts = db.execute('SELECT * FROM contact ORDER BY created_at DESC').fetchall()
    db.close()
    return render_template('admin_contacts.html', user=user, contacts=contacts)

@app.route('/admin/predictions')
def admin_predictions():
    user = get_current_user()
    if not require_admin(user):
        flash(t('admin_no_access'), 'error')
        return redirect(url_for('home'))
    db = get_db()
    preds = db.execute(
        "SELECT p.*, u.name as user_name, u.email as user_email "
        "FROM predictions p LEFT JOIN users u ON p.user_id=u.id "
        "ORDER BY p.created_at DESC LIMIT 200"
    ).fetchall()
    db.close()
    return render_template('admin_predictions.html', user=user, preds=preds)

@app.route('/admin/create-admin', methods=['GET', 'POST'])
def admin_create_admin():
    user = get_current_user()
    if not require_admin(user):
        flash(t('admin_no_access'), 'error')
        return redirect(url_for('home'))
    if request.method == 'POST':
        name     = request.form.get('name', '').strip()
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm_password', '')
        if not name or not email or not password:
            flash('All fields are required.', 'error')
        elif password != confirm:
            flash('Passwords do not match.', 'error')
        elif len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
        else:
            try:
                db = get_db()
                db.execute(
                    'INSERT INTO users (name, email, password_hash, credits, plan, is_admin) VALUES (?,?,?,?,?,1)',
                    (name, email, hash_password(password), 999999, 'enterprise')
                )
                db.commit()
                db.close()
                flash(t('admin_user_created'), 'success')
                return redirect(url_for('admin_users'))
            except sqlite3.IntegrityError:
                flash('Email already registered.', 'error')
    return render_template('admin_create_admin.html', user=user)

@app.route('/admin/make-admin/<int:uid>')
def admin_make_admin(uid):
    user = get_current_user()
    if not require_admin(user):
        flash(t('admin_no_access'), 'error')
        return redirect(url_for('home'))
    db = get_db()
    db.execute('UPDATE users SET is_admin=1 WHERE id=?', (uid,))
    db.commit()
    db.close()
    flash(t('admin_promoted'), 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/remove-admin/<int:uid>')
def admin_remove_admin(uid):
    user = get_current_user()
    if not require_admin(user):
        flash(t('admin_no_access'), 'error')
        return redirect(url_for('home'))
    if uid == user['id']:
        flash("You cannot remove your own admin privileges.", 'error')
        return redirect(url_for('admin_users'))
    db = get_db()
    db.execute('UPDATE users SET is_admin=0 WHERE id=?', (uid,))
    db.commit()
    db.close()
    flash(t('admin_demoted'), 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/delete-user/<int:uid>', methods=['POST'])
def admin_delete_user(uid):
    user = get_current_user()
    if not require_admin(user):
        flash(t('admin_no_access'), 'error')
        return redirect(url_for('home'))
    if uid == user['id']:
        flash("You cannot delete your own account from admin panel.", 'error')
        return redirect(url_for('admin_users'))
    db = get_db()
    db.execute('DELETE FROM predictions WHERE user_id=?', (uid,))
    db.execute('DELETE FROM users WHERE id=?', (uid,))
    db.commit()
    db.close()
    flash(t('admin_deleted'), 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/reset-credits/<int:uid>', methods=['POST'])
def admin_reset_credits(uid):
    user = get_current_user()
    if not require_admin(user):
        flash(t('admin_no_access'), 'error')
        return redirect(url_for('home'))
    credits = int(request.form.get('credits', FREE_CREDITS))
    db = get_db()
    db.execute('UPDATE users SET credits=? WHERE id=?', (credits, uid))
    db.commit()
    db.close()
    flash(f'Credits updated to {credits}.', 'success')
    return redirect(url_for('admin_users'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
