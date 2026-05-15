# Backend Error Rectification TODO

## 1. Fix dataset paths in `backend/train.py`
- [x] Change `pd.read_csv('dataset/urldata.csv')` to `pd.read_csv('../dataset/urldata.csv')`
- [x] Make email dataset path relative (`../dataset/CEAS_08.csv`)

## 2. Align `extract_email_address_features.py` with trained model
- [x] Update suspicious TLD list to match `train.py`
- [x] Update free domain list to match `train.py`
- [x] Fix domain "entropy" calculation to match `train.py` (`len(set(domain))/(len(domain)+1)`)

## 3. Remove duplicate feature code in `backend/train.py`
- [x] Delete inline `extract_email_address_features()`
- [x] Import from `extract_email_address_features.py`

## 4. Fix email-text feature skew in `backend/app.py`
- [x] `'bank'` already present in suspicious-words list — no change needed

## 5. Fix short-circuit response format in `backend/app.py`
- [x] Update early-return JSON in `/predict` to include `confidence_label`, `top_email_features`, `top_url_features`, `top_email_address_features`

## 6. Add SHAP error resilience in `backend/app.py`
- [x] Wrap `get_shap_by_category()` in `try/except` in `/predict`
- [x] Wrap `get_shap_by_category()` in `try/except` in `/predict_url`

## 7. Fix SHAP values showing "No significant features"
- [x] Handle `TreeExplainer.shap_values()` returning a list for binary classification (use positive class index 1)
- [x] Remove overly strict `1e-10` threshold — now only filters exact zeros
- [x] Added automatic fallback to perturbation-based feature importance when SHAP returns empty results
- [x] Fallback zeroes each feature individually and measures prediction probability change — model-agnostic and guaranteed to work

## Testing
- [x] `/predict` endpoint returns populated `top_email_features` and `top_url_features`
- [x] `/predict_url` endpoint returns populated `top_url_features`
- [x] Flask server running successfully on `http://127.0.0.1:5000`

## Known Limitation (Training Data, Not Backend Bug)
- `top_email_address_features` may appear empty for some inputs because the model was trained with a hardcoded email address (`user@example.com`) for all samples. The model never learned to differentiate based on sender email address features. To fix this, retrain `train.py` with varied email addresses in the training data.

