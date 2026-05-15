"""Baseplate Gmail integration helpers for OAuth2 and message retrieval."""
import os
from typing import Optional

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


def _import_google_libraries():
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        return InstalledAppFlow, build
    except ImportError as exc:
        raise ImportError(
            'Missing Google Gmail dependencies. Install google-auth-oauthlib and google-api-python-client.'
        ) from exc


def build_gmail_service(credentials_path='credentials.json', token_path='token.json'):
    InstalledAppFlow, build = _import_google_libraries()

    if not os.path.exists(credentials_path):
        raise FileNotFoundError(f'Credentials file not found: {credentials_path}')

    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
    creds = flow.run_local_server(port=0)
    service = build('gmail', 'v1', credentials=creds)
    return service


def list_unread_messages(service, max_results=10):
    results = service.users().messages().list(userId='me', labelIds=['UNREAD'], maxResults=max_results).execute()
    return results.get('messages', [])


def get_message_payload(service, message_id):
    message = service.users().messages().get(userId='me', id=message_id, format='full').execute()
    return message
