p# KisanMitra v2.0 — Enhanced

## New Features
1. **Multilingual Support** — English (default), Hindi (हिन्दी), Marathi (मराठी)
   - Switch language via navbar EN / हि / म buttons
   - Session-based language persistence

2. **Login & Signup System**
   - Secure password hashing (SHA-256)
   - User profile page with credit history

3. **Credit System**
   - New users get **200 FREE credits** on signup
   - Each prediction costs **5 credits**
   - Credits shown in navbar with progress bar
   - When credits run out → modal prompts upgrade

4. **Plans & Pricing**
   - Free: 200 one-time credits
   - Basic: ₹99/month → 500 credits
   - Pro: ₹249/month → 1500 credits (Most Popular)
   - Enterprise: ₹699/month → 5000 credits

## Running
```bash
pip install flask pillow numpy
python app.py
```
Visit: http://localhost:5000

## Database
SQLite (kisanmitra.db) — auto-created on first run.
Tables: users, predictions, feedback, contact
