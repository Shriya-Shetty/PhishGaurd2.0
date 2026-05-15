from flask import Flask, request, jsonify, send_from_directory
import xgboost as xgb
import numpy as np
import re
import os
import joblib

from feature_extraction import (
    extract_email_text_features,
    extract_urls,
    extract_url_features,
    extract_email_address_features,
    fuse_features,
    FEATURE_NAMES,
)
from settings import MODEL_PATHS
from model_ensemble import EnsembleClassifier
from shap_explainer import SHAPTopFeatures

app = Flask(__name__, static_folder='../frontend')


@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response


# ----------------- Load model + scaler -----------------
script_dir = os.path.dirname(os.path.abspath(__file__))

xgb_model = xgb.XGBClassifier(
    objective='binary:logistic',
    n_estimators=100,
    use_label_encoder=False,
    eval_metric='logloss',
)
model = xgb_model
ensemble_path = MODEL_PATHS.get('ensemble')
xgb_path = MODEL_PATHS.get('xgb')
scaler_path = MODEL_PATHS.get('scaler')

if ensemble_path and os.path.exists(ensemble_path):
    try:
        model = EnsembleClassifier.load(ensemble_path)
        print(f'Loaded ensemble model from {ensemble_path}')
    except Exception as e:
        print(f'Could not load ensemble model: {e}. Falling back to XGBoost baseline.')

if model is xgb_model and xgb_path and os.path.exists(xgb_path):
    xgb_model.load_model(xgb_path)

if scaler_path and os.path.exists(scaler_path):
    scaler = joblib.load(scaler_path)
else:
    raise FileNotFoundError(f'Scaler file not found: {scaler_path}')


# ----------------- Helpers -----------------

def clean_email_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def classify_phishing(features: np.ndarray) -> float:
    features_scaled = scaler.transform([features])
    return float(model.predict_proba(features_scaled)[0][1])


def generate_reasoning(email_text, url, email_address, prediction, probability, top_features):
    from llm_reasoning_ollama import ollama_chat

    is_phishing = prediction.lower() in {"phishing", "phishing website"}
    confidence = probability * 100

    # Flatten top_features dicts (feature->score)
    def _flatten(feat_dict):
        if not feat_dict or not isinstance(feat_dict, dict):
            return []
        items = []
        for k, v in feat_dict.items():
            try:
                fv = float(v)
            except Exception:
                fv = 0.0
            items.append((k, fv))
        items.sort(key=lambda x: abs(x[1]), reverse=True)
        return items

    pos = _flatten({k: v for k, v in top_features.items() if v > 0})
    neg = _flatten({k: v for k, v in top_features.items() if v < 0})

    positive_str = ", ".join([k for k, _ in pos[:5]])
    negative_str = ", ".join([k for k, _ in neg[:5]])

    prompt = (
        "You are a cybersecurity assistant helping analyze phishing risks. "
        "Write concise, user-friendly reasoning for a non-technical user. "
        "Include: (1) verdict, (2) 3-6 concrete indicators, (3) recommended actions.\n\n"
        f"Prediction: {prediction}\n"
        f"Confidence: {confidence:.1f}%\n\n"
        f"Email address: {email_address}\n"
        f"URL: {url}\n\n"
        "Email text:\n"
        f"{(email_text or '')[:2000]}\n\n"
        f"Positive indicators: {positive_str if positive_str else '(none)'}\n"
        f"Negative indicators: {negative_str if negative_str else '(none)'}\n\n"
        "Output:\n- Verdict: PHISHING or LEGITIMATE\n"
        "- Key indicators:\n  1) ...\n  2) ...\n  3) ...\n"
        "- Recommended actions:\n  1) ...\n  2) ...\n"
    )

    try:
        return ollama_chat(prompt, model="llama3")
    except Exception:
        # Fallback to simple heuristic
        reasoning_parts = []
        if is_phishing:
            reasoning_parts.append("⚠️ This content has been flagged as a potential PHISHING threat.")
        else:
            reasoning_parts.append("✅ This content appears to be LEGITIMATE.")
        reasoning_parts.append(f"\n📊 Confidence Score: {confidence:.1f}%")
        if pos:
            reasoning_parts.append("\n🔴 Risk indicators detected: " + ", ".join([k for k, _ in pos[:5]]))
        if neg:
            reasoning_parts.append("\n🟢 Trust indicators: " + ", ".join([k for k, _ in neg[:5]]))
        return "\n".join(reasoning_parts)


def calculate_risk_score(probability: float, top_features: dict, email_text: str, url: str) -> float:
    base_score = probability * 100
    adjustments = 0

    text_lower = (email_text or "").lower()
    url_lower = (url or "").lower()

    if any(word in text_lower for word in ['urgent', 'verify', 'password', 'click here', 'immediate', 'suspended']):
        adjustments += 10

    if url:
        if '-' in url or '@' in url or 'ip' in url_lower:
            adjustments += 15
        if not url.startswith('https'):
            adjustments += 10

    if top_features:
        high_impact = [k for k, v in top_features.items() if abs(v) > 0.3]
        adjustments += len(high_impact) * 5

    final_score = min(100, base_score + adjustments)
    return round(final_score, 1)


# ----------------- SHAP explainer -----------------
# Uses robust SHAP grouping + perturbation fallback inside SHAPTopFeatures.
shap_helper = SHAPTopFeatures(model, scaler)



@app.route('/predict', methods=['POST'])
def predict():
    data = request.json

    email_text = clean_email_text(data.get('email_text', ''))
    email_address = data.get('email_address', '')

    urls = extract_urls(email_text)
    url_from_email = urls[0] if urls else ''

    if len(email_text.strip()) < 25 and not any(w in email_text.lower() for w in ['click', 'verify', 'password', 'login', 'pay', 'urgent']):
        return jsonify({
            'probability': 0.2,
            'classification': 'Legitimate',
            'confidence_label': '20.0%',
            'top_email_features': {},
            'top_url_features': {},
            'top_email_address_features': {},
            'reasoning': 'Email is too short to analyze properly. No suspicious keywords detected.',
            'risk_score': 20.0
        })

    email_text_feats = extract_email_text_features(email_text)
    url_features = [extract_url_features(u) for u in urls]
    email_addr_feats = extract_email_address_features(email_address)

    fused = fuse_features(email_text_feats, url_features, email_addr_feats)

    prob = classify_phishing(fused)
    classification = 'Phishing' if prob > 0.7 else 'Legitimate'

    top_by_cat = shap_helper.explain_top_features_by_category(fused)

    all_top = {**top_by_cat.get('email_text', {}), **top_by_cat.get('url', {}), **top_by_cat.get('email_address', {})}

    reasoning = generate_reasoning(email_text, url_from_email, email_address, classification, prob, all_top)
    risk_score = calculate_risk_score(prob, all_top, email_text, url_from_email)

    return jsonify({
        'probability': float(prob),
        'classification': classification,
        'confidence_label': f"{(prob * 100):.1f}%",
        'top_email_features': top_by_cat.get('email_text', {}),
        'top_url_features': top_by_cat.get('url', {}),
        'top_email_address_features': top_by_cat.get('email_address', {}),
        'reasoning': reasoning,
        'risk_score': risk_score
    })


@app.route('/predict_url', methods=['POST'])
def predict_url():
    data = request.json
    url = data.get('url', '')

    url_feats = extract_url_features(url)

    email_text_feats = np.zeros(6)
    email_addr_feats = np.zeros(8)

    fused = np.concatenate([email_text_feats, url_feats, email_addr_feats])

    prob = classify_phishing(fused)
    classification = 'Phishing Website' if prob > 0.5 else 'Safe Website'

    top_by_cat = shap_helper.explain_top_features_by_category(fused)
    url_top = top_by_cat.get('url', {})

    reasoning = generate_reasoning('', url, '', classification, prob, url_top)
    risk_score = calculate_risk_score(prob, url_top, '', url)

    return jsonify({
        'probability': float(prob),
        'classification': classification,
        'confidence_label': f"{(prob * 100):.1f}%",
        'top_url_features': url_top,
        'reasoning': reasoning,
        'risk_score': risk_score
    })


@app.route('/')
def index():
    return send_from_directory('../frontend', 'index.html')


if __name__ == '__main__':
    app.run(debug=True)

