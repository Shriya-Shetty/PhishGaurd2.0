"""Simple SQLite persistence helpers for PhishGuard predictions and feedback."""

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

DB_PATH = Path(__file__).resolve().parent / 'phishguard.db'


def _table_columns(cursor: sqlite3.Cursor, table_name: str) -> List[str]:
    cursor.execute(f"PRAGMA table_info({table_name})")
    cols = cursor.fetchall()
    # PRAGMA table_info columns: cid, name, type, notnull, dflt_value, pk
    return [c[1] for c in cols]


def _ensure_gmail_messages_schema(cursor: sqlite3.Cursor) -> None:
    """Repair/upgrade gmail_messages table in-place if an older schema exists.

    This is needed because the repo has evolved over time; existing local
    SQLite DBs may miss columns like thread_id/to_address/snippet.
    """

    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS gmail_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            message_id TEXT UNIQUE,
            thread_id TEXT,
            internal_date TEXT,
            from_address TEXT,
            to_address TEXT,
            subject TEXT,
            snippet TEXT,
            raw_text TEXT,
            prediction_id INTEGER,
            classification TEXT,
            probability REAL,
            reason TEXT
        )
        '''
    )

    cols = set(_table_columns(cursor, 'gmail_messages'))

    # Only add columns if missing (SQLite supports ADD COLUMN; no ALTER TYPE).
    # Keep types simple.
    desired_missing = {
        'thread_id': 'TEXT',
        'internal_date': 'TEXT',
        'to_address': 'TEXT',
        'subject': 'TEXT',
        'snippet': 'TEXT',
        'raw_text': 'TEXT',
        'prediction_id': 'INTEGER',
        'classification': 'TEXT',
        'probability': 'REAL',
        'reason': 'TEXT',
    }

    for col, col_type in desired_missing.items():
        if col not in cols:
            cursor.execute(f"ALTER TABLE gmail_messages ADD COLUMN {col} {col_type}")


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

        _ensure_gmail_messages_schema(cursor)

        # Optional: also ensure predictions has expected columns.
        # (Safe no-op for fresh DBs; fixes older local DBs.)
        pred_cols = set(_table_columns(cursor, 'predictions'))
        if 'url' not in pred_cols:
            cursor.execute("ALTER TABLE predictions ADD COLUMN url TEXT")
        if 'reason' not in pred_cols:
            cursor.execute("ALTER TABLE predictions ADD COLUMN reason TEXT")
        if 'email_address' not in pred_cols:
            cursor.execute("ALTER TABLE predictions ADD COLUMN email_address TEXT")

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
