import sqlite3, os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'phishguard.db')
RETRAIN_THRESHOLD = 100

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_feedback_table():
    conn = get_conn()
    conn.execute('''CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email_id TEXT,
        email_text TEXT,
        predicted_label TEXT,
        predicted_probability REAL,
        actual_label TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

def save_feedback(email_id, email_text, predicted_label, predicted_probability, actual_label):
    conn = get_conn()
    conn.execute(
        'INSERT INTO feedback (email_id,email_text,predicted_label,predicted_probability,actual_label,timestamp) VALUES (?,?,?,?,?,?)',
        (str(email_id), email_text, predicted_label, predicted_probability, actual_label, datetime.utcnow())
    )
    conn.commit()
    count = conn.execute('SELECT COUNT(*) FROM feedback').fetchone()[0]
    conn.close()
    if count % RETRAIN_THRESHOLD == 0:
        _trigger_retrain(count)
    return count

def get_feedback_stats():
    conn = get_conn()
    total   = conn.execute('SELECT COUNT(*) FROM feedback').fetchone()[0]
    correct = conn.execute('SELECT COUNT(*) FROM feedback WHERE predicted_label=actual_label').fetchone()[0]
    conn.close()
    return {'total': total, 'correct': correct, 'accuracy': round((correct/total)*100, 2) if total else 0.0}

def get_all_feedback():
    conn = get_conn()
    rows = conn.execute('SELECT * FROM feedback ORDER BY timestamp DESC').fetchall()
    conn.close()
    return [dict(r) for r in rows]

def _trigger_retrain(count):
    print(f'[Feedback] {count} samples — triggering retraining...')
    try:
        from celery_config import retrain_model
        retrain_model.delay()
    except Exception as e:
        print(f'[Feedback] Retrain trigger skipped: {e}')