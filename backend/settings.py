"""Base configuration and paths for the PhishGuard backend."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATASET_DIR = BASE_DIR.parent / 'dataset'
MODEL_DIR = BASE_DIR

DATASET_PATHS = {
    'email': str(DATASET_DIR / 'CEAS_08.csv'),
    'url': str(DATASET_DIR / 'urldata.csv'),
}

MODEL_PATHS = {
    'xgb': str(MODEL_DIR / 'xgb_model.json'),
    'scaler': str(MODEL_DIR / 'scaler.pkl'),
    'ensemble': str(MODEL_DIR / 'ensemble_model.pkl'),
}

FEATURE_DIMENSIONS = {
    'email_text': 6,
    'url': 25,
    'email_address': 8,
}

DEFAULT_VOTING = 'soft'
