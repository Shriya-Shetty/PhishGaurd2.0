import base64
import json
from typing import Dict, Any, Optional, Tuple, List

from gmail_api import list_unread_messages, get_message_payload
from db import init_db



def _b64decode(data: str) -> bytes:
    # Gmail uses URL-safe base64; may be padded or not.
    data = data.replace('-', '+').replace('_', '/')
    pad = '=' * (-len(data) % 4)
    return base64.b64decode(data + pad)


def _walk_parts(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    parts = []

    def _collect(p: Dict[str, Any]):
        if not p:
            return
        if p.get('parts'):
            for sp in p.get('parts'):
                _collect(sp)
        else:
            parts.append(p)

    _collect(payload)
    return parts


def extract_headers(payload: Dict[str, Any]) -> Dict[str, str]:
    headers = payload.get('headers') or []
    out: Dict[str, str] = {}
    for h in headers:
        name = (h.get('name') or '').strip().lower()
        value = h.get('value') or ''
        if name:
            out[name] = value
    return out


def extract_best_effort_body(message_payload: Dict[str, Any]) -> Tuple[str, str]:
    """Return (snippet, raw_text). raw_text is best-effort extracted textual body."""
    snippet = message_payload.get('snippet') or ''
    payload = message_payload.get('payload') or {}

    parts = _walk_parts(payload)
    texts: List[str] = []

    for p in parts:
        mime_type = (p.get('mimeType') or '').lower()
        body = p.get('body') or {}
        data = body.get('data')
        if not data:
            continue

        # Prefer plain text; fallback to html stripped-ish.
        try:
            decoded = _b64decode(data).decode('utf-8', errors='ignore')
        except Exception:
            continue

        if decoded.strip():
            if 'text/plain' in mime_type:
                texts.append(decoded)
            elif 'text/html' in mime_type:
                # Minimal strip to keep features extraction simple.
                stripped = decoded.replace('<br>', '\n').replace('<br/>', '\n').replace('</p>', '\n')
                stripped = stripped.replace('<p>', '').replace('</div>', '\n').replace('<div>', '')
                texts.append(stripped)

    raw_text = '\n'.join(t for t in texts if t).strip()
    return snippet, raw_text


def process_unread_messages(
    service,
    classify_fn,
    db_path: Optional[str] = None,
    max_messages: int = 10,
) -> List[Dict[str, Any]]:
    """Process unread Gmail messages and persist predictions into SQLite.

    classify_fn must accept: (email_text, email_address) and return the same dict
    as the existing /predict route's jsonify payload (minus any Flask-specific stuff).
    """

    db_file = init_db(db_path)

    results: List[Dict[str, Any]] = []
    unread = list_unread_messages(service, max_results=max_messages)

    for m in unread:
        message_id = m.get('id')
        if not message_id:
            continue


        message = get_message_payload(service, message_id)
        hdrs = extract_headers(message.get('payload') or {})

        from_address = hdrs.get('from', '')
        subject = hdrs.get('subject', '')
        internal_date = message.get('internalDate')
        # Gmail headers can be complex; we keep to/address as best-effort.
        to_address = hdrs.get('to', '')

        snippet, raw_text = extract_best_effort_body(message)
        email_text = (raw_text or snippet or '').strip()

        classification_payload = classify_fn(email_text=email_text, email_address=from_address)

        # Persist: reuse existing predictions table plus gmail_messages table.
        from db import save_prediction

        pred_row = {
            'classification': classification_payload.get('classification'),
            'probability': classification_payload.get('probability'),
            'email_address': from_address,
            'url': '',
            'reason': classification_payload.get('reasoning') or classification_payload.get('reason') or '',
        }
        prediction_id = save_prediction(pred_row, db_path=db_file)

        # Save gmail message record with prediction linkage.
        import sqlite3
        from pathlib import Path

        dbf = Path(db_file)
        with sqlite3.connect(dbf) as conn:
            cur = conn.cursor()
            cur.execute(
                '''
                INSERT OR IGNORE INTO gmail_messages (
                    message_id, thread_id, internal_date,
                    from_address, to_address, subject,
                    snippet, raw_text,
                    prediction_id, classification, probability, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    message.get('id'),
                    (message.get('threadId') or ''),
                    internal_date,
                    from_address,
                    to_address,
                    subject,
                    snippet,
                    raw_text,
                    prediction_id,
                    classification_payload.get('classification'),
                    float(classification_payload.get('probability')) if classification_payload.get('probability') is not None else None,
                    classification_payload.get('reasoning') or '',
                ),
            )
            conn.commit()

        results.append(
            {
                'message_id': message_id,
                'from_address': from_address,
                'subject': subject,
                'classification': classification_payload.get('classification'),
                'probability': classification_payload.get('probability'),
                'risk_score': classification_payload.get('risk_score'),
            }
        )

        # Mark the message as read
        try:
            service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
        except Exception as e:
            print(f"Failed to mark message {message_id} as read: {e}")

    return results


