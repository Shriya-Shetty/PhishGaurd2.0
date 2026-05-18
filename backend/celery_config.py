from celery import Celery
from celery.schedules import crontab
import os, subprocess

REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

celery_app = Celery('phishguard', broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.update(task_serializer='json', result_serializer='json', accept_content=['json'], timezone='Asia/Kolkata')

celery_app.conf.beat_schedule = {
    'process-email-batch': {
        'task': 'celery_config.process_email_batch',
        'schedule': 300.0,
    },
    'weekly-report': {
        'task': 'celery_config.generate_weekly_report',
        'schedule': crontab(hour=9, minute=0, day_of_week='monday'),
    }
}

@celery_app.task(name='celery_config.process_email_batch')
def process_email_batch():
    print('[Celery] Processing email batch...')
    try:
        import sqlite3, requests
        DB_PATH = os.path.join(os.path.dirname(__file__), 'phishguard.db')
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("SELECT id,email_text,sender_email FROM emails WHERE status='pending' LIMIT 50").fetchall()
        for (eid, text, sender) in rows:
            try:
                r = requests.post('http://127.0.0.1:5000/predict', json={'email_text': text, 'email_address': sender or 'unknown@unknown.com'}, timeout=10)
                if r.status_code == 200:
                    res = r.json()
                    conn.execute("UPDATE emails SET status='processed',risk_score=?,classification=? WHERE id=?",
                                 (res.get('risk_score',0), res.get('classification','Unknown'), eid))
            except Exception as e:
                print(f'[Celery] Email {eid} failed: {e}')
        conn.commit()
        conn.close()
        print(f'[Celery] Done. Processed {len(rows)} emails.')
    except Exception as e:
        print(f'[Celery] Batch error: {e}')

@celery_app.task(name='celery_config.retrain_model')
def retrain_model():
    print('[Celery] Retraining model...')
    result = subprocess.run(
        ['python', os.path.join(os.path.dirname(__file__), 'ensemble_train.py')],
        capture_output=True, text=True
    )
    print('[Celery] Retrain done.' if result.returncode == 0 else f'[Celery] Retrain failed: {result.stderr}')

@celery_app.task(name='celery_config.generate_weekly_report')
def generate_weekly_report():
    from feedback_collector import get_feedback_stats
    stats = get_feedback_stats()
    report = f"=== PhishGuard Weekly Report ===\nFeedback total: {stats['total']}\nCorrect: {stats['correct']}\nAccuracy: {stats['accuracy']}%\n"
    print(report)
    with open(os.path.join(os.path.dirname(__file__), '..', 'weekly_report.txt'), 'w') as f:
        f.write(report)