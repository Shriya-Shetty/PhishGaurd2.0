"""Simple SQLite persistence helpers for PhishGuard predictions and feedback."""
import sqlite3
from pathlib import Path
from typing import Dict, List

DB_PATH = Path(__file__).resolve().parent / 'phishguard.db'


def init_db(db_path: str = None):
    db_file = DB_PATH if db_path is None else Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                classification TEXT,
                probability REAL,
                email_address TEXT,
                url TEXT,
                reason TEXT
            )
            '''
        )
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prediction_id INTEGER,
                correct INTEGER,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            '''
        )
        conn.commit()
    return str(db_file)


def save_prediction(record: Dict, db_path: str = None):
    db_file = DB_PATH if db_path is None else Path(db_path)
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT INTO predictions (classification, probability, email_address, url, reason)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (
                record.get('classification'),
                record.get('probability'),
                record.get('email_address'),
                record.get('url'),
                record.get('reason'),
            )
        )
        conn.commit()
        return cursor.lastrowid


def get_recent_predictions(limit: int = 50, db_path: str = None) -> List[Dict]:
    db_file = DB_PATH if db_path is None else Path(db_path)
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, created_at, classification, probability, email_address, url, reason FROM predictions ORDER BY id DESC LIMIT ?',
            (limit,),
        )
        rows = cursor.fetchall()
    return [
        {
            'id': row[0],
            'created_at': row[1],
            'classification': row[2],
            'probability': row[3],
            'email_address': row[4],
            'url': row[5],
            'reason': row[6],
        }
        for row in rows
    ]
