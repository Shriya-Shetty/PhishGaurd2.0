import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score
import xgboost as xgb
import joblib

from feature_extraction import (
    extract_email_text_features,
    extract_urls,
    extract_url_features,
    extract_email_address_features,
)
from settings import DATASET_PATHS, MODEL_PATHS


def _read_csv_safe(path: str, *, nrows: int | None = None) -> pd.DataFrame:
    """Safer CSV loading: disables low_memory chunking and forces strings for text columns."""
    return pd.read_csv(
        path,
        low_memory=False,
        nrows=nrows,
    )


def _clean_binary_labels(series: pd.Series, mapping: dict[str, int]) -> pd.Series:
    s = series.astype(str).str.strip().str.lower()
    return s.map(mapping).fillna(0).astype(int)


# -----------------------------
# LOAD DATASETS
# -----------------------------

email_df = _read_csv_safe(DATASET_PATHS['email'])

# Detect columns automatically
email_col = next((c for c in email_df.columns if 'body' in c.lower()), None)
if email_col is None:
    # fallback: also try 'text'
    email_col = next((c for c in email_df.columns if 'text' in c.lower()), None)
if email_col is None:
    raise Exception("Email body/text column not found in CEAS_08.csv")

label_col = next((c for c in email_df.columns if 'label' in c.lower()), None)
if label_col is None:
    raise Exception("Label column not found in CEAS_08.csv")

# Keep only required columns, handle missing values
email_df = email_df[[email_col, label_col]].copy()
email_df.columns = ['text', 'label']
email_df['text'] = email_df['text'].fillna('')

# label cleaning
email_df['label'] = _clean_binary_labels(
    email_df['label'],
    {
        'spam': 1,
        'phishing': 1,
        '1': 1,
        'ham': 0,
        'legitimate': 0,
        '0': 0,
        'bad': 1,
        'good': 0,
    },
)

# Downsample to keep training fast
email_df = email_df.sample(n=min(5000, len(email_df)), random_state=42) if len(email_df) else email_df

# URL dataset
url_df = _read_csv_safe(DATASET_PATHS['url'])

# Detect URL + label columns
url_col = next((c for c in url_df.columns if c.lower() == 'url' or 'url' in c.lower()), None)
if url_col is None:
    raise Exception("URL column not found in urldata.csv")
label_col_url = next((c for c in url_df.columns if 'label' in c.lower()), None)
if label_col_url is None:
    raise Exception("Label column not found in urldata.csv")

url_df = url_df[[url_col, label_col_url]].copy()
url_df.columns = ['url', 'label']
url_df['url'] = url_df['url'].fillna('')

url_df['label'] = _clean_binary_labels(url_df['label'], {'bad': 1, 'good': 0, '1': 1, '0': 0})

url_df = url_df.sample(n=min(5000, len(url_df)), random_state=42) if len(url_df) else url_df


# -----------------------------
# FEATURE EXTRACTION
# -----------------------------

X: list[np.ndarray] = []
y: list[int] = []

EMAIL_ADDR_FEATS = extract_email_address_features("user@example.com")

# EMAIL DATA
for _, row in email_df.iterrows():
    try:
        text = str(row['text'] or '')
        label = int(row['label'])

        email_feats = extract_email_text_features(text)
        urls = extract_urls(text)
        url_feats = [extract_url_features(u) for u in urls if u]

        if url_feats:
            avg_url = np.mean(url_feats, axis=0)
        else:
            avg_url = np.zeros(25, dtype=float)

        features = np.concatenate([email_feats, avg_url, EMAIL_ADDR_FEATS]).astype(float)

        if features.shape[0] != 39:
            # Skip malformed feature vectors without using random padding
            continue

        X.append(features)
        y.append(label)
    except Exception:
        # error protection for malformed rows
        continue

# URL DATA
for _, row in url_df.iterrows():
    try:
        url = str(row['url'] or '')
        label = int(row['label'])

        email_feats = extract_email_text_features(url)  # simulate email-text features from URL
        url_feats = extract_url_features(url)
        features = np.concatenate([email_feats, url_feats, EMAIL_ADDR_FEATS]).astype(float)

        if features.shape[0] != 39:
            continue

        X.append(features)
        y.append(label)
    except Exception:
        continue

if not X:
    raise RuntimeError("No training examples were generated. Check dataset schema/feature extraction.")

X = np.array(X, dtype=float)
y = np.array(y, dtype=int)


# -----------------------------
# TRAIN
# -----------------------------

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

model = xgb.XGBClassifier(
    objective='binary:logistic',
    n_estimators=400,
    learning_rate=0.05,
    max_depth=5,
    subsample=0.8,
    colsample_bytree=0.8,
    reg_lambda=1.0,
    eval_metric='logloss',
    random_state=42,
)

model.fit(X_train_scaled, y_train)

# Accuracy output
pred = model.predict(X_test_scaled)
acc = accuracy_score(y_test, pred)
print(f"✅ XGBoost validation accuracy: {acc:.4f}")


# -----------------------------
# SAVE
# -----------------------------

model.save_model(MODEL_PATHS['xgb'])
joblib.dump(scaler, MODEL_PATHS['scaler'])

print(f"✅ Model trained with EMAIL + URL features and saved to {MODEL_PATHS['xgb']}")

