"""Basic ensemble wrapper for XGBoost, RandomForest, and LightGBM models."""
import os
import joblib
import numpy as np
from sklearn.ensemble import VotingClassifier, RandomForestClassifier
import xgboost as xgb

try:
    from lightgbm import LGBMClassifier
except ImportError:
    LGBMClassifier = None


def _make_estimators():
    estimators = [
        ('xgb', xgb.XGBClassifier(objective='binary:logistic', n_estimators=100, use_label_encoder=False, eval_metric='logloss')),
        ('rf', RandomForestClassifier(n_estimators=100, random_state=42)),
    ]
    if LGBMClassifier is not None:
        estimators.append(('lgbm', LGBMClassifier(n_estimators=100)))
    return estimators


class EnsembleClassifier:
    def __init__(self, voting='soft'):
        self.voting = voting
        self.model = VotingClassifier(estimators=_make_estimators(), voting=voting, flatten_transform=True)
        self.scaler = None

    def fit(self, X, y):
        self.scaler = joblib.load('scaler.pkl') if os.path.exists('scaler.pkl') else None
        self.model.fit(X, y)
        return self

    def predict_proba(self, X):
        return self.model.predict_proba(X)

    def predict(self, X):
        return self.model.predict(X)

    def save(self, path, scaler_path=None):
        joblib.dump(self, path)
        if scaler_path and self.scaler is not None:
            joblib.dump(self.scaler, scaler_path)

    @classmethod
    def load(cls, path):
        return joblib.load(path)
