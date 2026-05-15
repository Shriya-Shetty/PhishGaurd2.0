"""Baseplate ensemble training script for PhishGuard."""
import sys
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from feature_extraction import (
    extract_email_text_features,
    extract_urls,
    extract_url_features,
    extract_email_address_features,
    fuse_features,
)
from model_ensemble import EnsembleClassifier
from settings import DATASET_PATHS, MODEL_PATHS


def load_datasets():
    email_df = pd.read_csv(DATASET_PATHS['email'])
    url_df = pd.read_csv(DATASET_PATHS['url'])
    return email_df, url_df


def normalize_labels(df, label_column):
    df[label_column] = df[label_column].astype(str).str.lower().map({
        'spam': 1, 'phishing': 1, '1': 1,
        'ham': 0, 'legitimate': 0, '0': 0,
        'bad': 1, 'good': 0,
    }).fillna(0).astype(int)
    return df


def build_feature_matrix(email_df, url_df):
    X = []
    y = []

    for _, row in email_df.head(2000).iterrows():
        text = str(row.get('body') or row.get('text') or '')
        label = int(row.get('label', 0))
        email_feats = extract_email_text_features(text)
        url_feats = [extract_url_features(u) for u in extract_urls(text)]
        email_addr_feats = extract_email_address_features('user@example.com')
        features = fuse_features(email_feats, url_feats, email_addr_feats)
        X.append(features)
        y.append(label)

    for _, row in url_df.head(2000).iterrows():
        url = str(row.get('url') or '')
        label = int(row.get('label', 0))
        email_feats = extract_email_text_features(url)
        url_feats = [extract_url_features(url)]
        email_addr_feats = extract_email_address_features('user@example.com')
        features = fuse_features(email_feats, url_feats, email_addr_feats)
        X.append(features)
        y.append(label)

    return np.array(X), np.array(y)


def main():
    try:
        email_df, url_df = load_datasets()
    except FileNotFoundError as exc:
        print(f'Error loading dataset: {exc}')
        sys.exit(1)

    email_df = normalize_labels(email_df, 'label')
    url_df = normalize_labels(url_df, 'label')

    X, y = build_feature_matrix(email_df, url_df)
    if len(X) == 0:
        print('No training examples were generated. Please verify the dataset schema.')
        sys.exit(1)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    model = EnsembleClassifier(voting='soft')
    model.fit(X_train_scaled, y_train)
    model.scaler = scaler
    model.save(MODEL_PATHS['ensemble'], scaler_path=MODEL_PATHS['scaler'])

    score = model.model.score(X_test_scaled, y_test)
    print(f'✅ Ensemble training complete. Validation accuracy: {score:.4f}')
    print(f'✅ Saved ensemble model to {MODEL_PATHS["ensemble"]}')


if __name__ == '__main__':
    main()
