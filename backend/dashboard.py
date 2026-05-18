from flask import Blueprint, jsonify, request, send_from_directory
import sqlite3, os
from feedback_collector import save_feedback, get_feedback_stats

dashboard_bp = Blueprint('dashboard', __name__)
DB_PATH = os.path.join(os.path.dirname(__file__), 'phishguard.db')
FRONTEND = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''CREATE TABLE IF NOT EXISTS emails (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_email TEXT,
        email_text TEXT,
        status TEXT DEFAULT 'processed',
        risk_score REAL,
        classification TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

init_db()  # run on import



def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@dashboard_bp.route('/dashboard')
def dashboard():
    return send_from_directory(FRONTEND, 'dashboard.html')

@dashboard_bp.route('/api/emails')
def api_emails():
    status = request.args.get('status', 'all')
    limit  = request.args.get('limit', 100, type=int)
    conn   = get_db()
    q = 'SELECT * FROM emails ORDER BY id DESC LIMIT ?' if status == 'all' else 'SELECT * FROM emails WHERE status=? ORDER BY id DESC LIMIT ?'
    rows = conn.execute(q, (limit,) if status == 'all' else (status, limit)).fetchall()
    conn.close()
    emails = []
    for r in rows:
        d = dict(r)
        d['preview'] = (d.get('email_text') or '')[:120]
        emails.append(d)
    return jsonify({'emails': emails, 'count': len(emails)})

@dashboard_bp.route('/api/email/<int:email_id>')
def api_email_detail(email_id):
    conn = get_db()
    row  = conn.execute('SELECT * FROM emails WHERE id=?', (email_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'Not found'}), 404
    email = dict(row)
    if not email.get('classification') and email.get('email_text'):
        import requests
        try:
            r = requests.post('http://127.0.0.1:5000/predict', json={'email_text': email['email_text'], 'email_address': email.get('sender_email','unknown@unknown.com')}, timeout=15)
            if r.status_code == 200:
                email.update(r.json())
        except Exception as e:
            email['analysis_error'] = str(e)
    return jsonify(email)

@dashboard_bp.route('/api/metrics')
def api_metrics():
    stats = get_feedback_stats()
    model_info = {}
    try:
        p = os.path.join(os.path.dirname(__file__), 'ensemble_model.pkl')
        if os.path.exists(p):
            from datetime import datetime
            model_info = {'model_type': 'Ensemble (XGBoost + RF + LightGBM)', 'last_trained': datetime.fromtimestamp(os.path.getmtime(p)).strftime('%Y-%m-%d %H:%M')}
        else:
            model_info = {'model_type': 'XGBoost baseline', 'last_trained': '—'}
    except Exception:
        model_info = {'model_type': 'Unknown', 'last_trained': '—'}
    return jsonify({'feedback': stats, 'model': model_info, 'feedback_threshold': 100})

@dashboard_bp.route('/api/feedback', methods=['POST'])
def api_feedback():
    d = request.get_json() or {}
    for f in ['email_id','predicted_label','actual_label']:
        if f not in d:
            return jsonify({'error': f'Missing: {f}'}), 400
    count = save_feedback(d['email_id'], d.get('email_text',''), d['predicted_label'], d.get('predicted_probability',0.0), d['actual_label'])
    return jsonify({'success': True, 'total_feedback': count, 'retraining_triggered': count % 100 == 0})

@dashboard_bp.route('/webhook/gmail', methods=['POST'])
def gmail_webhook():
    import base64, json
    envelope = request.get_json() or {}
    try:
        data = base64.b64decode(envelope.get('message',{}).get('data','')).decode()
        print(f'[Webhook] Gmail notification: {json.loads(data)}')
    except Exception as e:
        print(f'[Webhook] Decode error: {e}')
    return 'OK', 200