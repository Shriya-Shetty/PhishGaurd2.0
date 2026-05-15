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


# Enable CORS
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Load model
script_dir = os.path.dirname(os.path.abspath(__file__))

xgb_model = xgb.XGBClassifier(objective='binary:logistic', n_estimators=100, use_label_encoder=False, eval_metric='logloss')
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

# Lazy load DistilBERT model (to save memory)

distilbert_model = None

def get_distilbert_model():
    global distilbert_model
    if distilbert_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            print("Loading DistilBERT model...")
            distilbert_model = SentenceTransformer('distilbert-base-uncased')
            print("DistilBERT model loaded successfully!")
        except Exception as e:
            print(f"Warning: Could not load DistilBERT: {e}")
            return None
    return distilbert_model

# -----------------------------
# TEXT PROCESSING

def clean_email_text(text):
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

# -----------------------------
# MODEL PREDICTION

def classify_phishing(features):
    features_scaled = scaler.transform([features])
    return float(model.predict_proba(features_scaled)[0][1])

# -----------------------------
# SHAP Top Features (rewritten, cached)
# -----------------------------

shap_top = SHAPTopFeatures(model=model, scaler=scaler, feature_names=FEATURE_NAMES)

# -----------------------------
# DISTILBERT EMBEDDINGS
# -----------------------------

def get_text_embedding(text):
    """Get DistilBERT embedding for text"""
    model = get_distilbert_model()

    if model is None:
        return np.zeros(768)  # Return zeros if model not available
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding

def get_combined_embedding(email_text, url, email_address):
    """Combine embeddings from email, URL, and email address"""
    # Get individual embeddings
    email_emb = get_text_embedding(email_text[:512])  # Truncate to max length
    
    # For URL, create a description
    url_desc = f"URL: {url}"
    url_emb = get_text_embedding(url_desc)
    
    # For email address
    email_addr_emb = get_text_embedding(email_address)
    
    # Combine embeddings (average)
    combined = (email_emb + url_emb + email_addr_emb) / 3
    
    return combined

# -----------------------------
# LLAMA REASONING
# -----------------------------

def generate_reasoning(email_text, url, email_address, prediction, probability, top_features):
    """Generate human-readable reasoning using Llama-style analysis"""
    
    # Analyze key factors from SHAP values
    positive_factors = [k for k, v in top_features.items() if v > 0]
    negative_factors = [k for k, v in top_features.items() if v < 0]
    
    is_phishing = prediction.lower() == "phishing" or prediction.lower() == "phishing website"
    confidence = probability * 100
    
    # Build reasoning
    reasoning_parts = []
    
    if is_phishing:
        reasoning_parts.append("⚠️ This content has been flagged as a potential PHISHING threat.")
    else:
        reasoning_parts.append("✅ This content appears to be LEGITIMATE.")
    
    reasoning_parts.append(f"\n📊 Confidence Score: {confidence:.1f}%")
    
    if positive_factors:
        reasoning_parts.append(f"\n🔴 Risk indicators detected: {', '.join(positive_factors[:5])}")
    
    if negative_factors:
        reasoning_parts.append(f"\n🟢 Trust indicators: {', '.join(negative_factors[:5])}")
    
    # Add specific observations based on content
    text_lower = email_text.lower() if email_text else ""
    url_lower = url.lower() if url else ""
    
    if any(word in text_lower for word in ['urgent', 'verify', 'password', 'click here', 'account']):
        reasoning_parts.append("\n⚡ Urgent language detected - common in phishing attempts")
    
    if '@' in email_address and any(domain in email_address.lower() for domain in ['gmail.com', 'yahoo.com', 'hotmail.com']):
        reasoning_parts.append("\n📧 Free email provider detected - verify sender authenticity")
    
    if url and not url.startswith('https'):
        reasoning_parts.append("\n🔒 Non-secure connection (HTTP instead of HTTPS)")
    
    return "\n".join(reasoning_parts)

# -----------------------------
# RISK SCORE CALCULATION
# -----------------------------

def calculate_risk_score(probability, top_features, email_text, url):
    """Calculate overall risk score (0-100)"""
    base_score = probability * 100
    
    # Adjust based on content analysis
    adjustments = 0
    
    text_lower = email_text.lower() if email_text else ""
    url_lower = url.lower() if url else ""
    
    # High-risk keywords
    if any(word in text_lower for word in ['urgent', 'verify', 'password', 'click here', 'immediate', 'suspended']):
        adjustments += 10
    
    # Suspicious URL patterns
    if url:
        if '-' in url or '@' in url or 'ip' in url_lower:
            adjustments += 15
        if not url.startswith('https'):
            adjustments += 10
    
    # Adjust based on SHAP feature importance
    if top_features:
        high_impact_features = [k for k, v in top_features.items() if abs(v) > 0.3]
        adjustments += len(high_impact_features) * 5
    
    final_score = min(100, base_score + adjustments)
    return round(final_score, 1)

# -----------------------------
# ROUTES
# -----------------------------

@app.route('/predict', methods=['POST'])
def predict():
    data = request.json

    email_text = clean_email_text(data.get('email_text', ''))
    text_lower = email_text.lower()

    suspicious_words = ['click', 'verify', 'password', 'login', 'pay', 'urgent']

    # Handle short emails safely
    if len(email_text.strip()) < 25:
        if not any(word in text_lower for word in suspicious_words):
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
    email_address = data.get('email_address', '')

    email_text_feats = extract_email_text_features(email_text)

    urls = extract_urls(email_text)
    url_features = [extract_url_features(url) for url in urls]

    email_addr_feats = extract_email_address_features(email_address)

    fused = fuse_features(email_text_feats, url_features, email_addr_feats)

    prob = classify_phishing(fused)
    classification = 'Phishing' if prob > 0.7 else 'Legitimate'

    try:
        shap_categories = shap_top.explain_top_features_by_category(fused, top_k=5)
    except Exception as e:
        print(f"SHAP explanation failed: {e}")
        shap_categories = {'email_text': {}, 'url': {}, 'email_address': {}}

    
    # Generate reasoning from all real features combined
    url_from_email = urls[0] if urls else ''
    all_shap = {**shap_categories['email_text'], **shap_categories['url'], **shap_categories['email_address']}
    reasoning = generate_reasoning(email_text, url_from_email, email_address, classification, prob, all_shap)
    
    # Calculate risk score
    risk_score = calculate_risk_score(prob, all_shap, email_text, url_from_email)

    return jsonify({
        'probability': float(prob),
        'classification': classification,
        'confidence_label': f"{(prob * 100):.1f}%",
        'top_email_features': shap_categories['email_text'],
        'top_url_features': shap_categories['url'],
        'top_email_address_features': shap_categories['email_address'],
        'reasoning': reasoning,
        'risk_score': risk_score
    })

@app.route('/predict_url', methods=['POST'])
def predict_url():
    data = request.json
    url = data.get('url', '')

    # Extract URL features
    url_feats = extract_url_features(url)

    # Empty email + sender features (to match model input size)
    email_text_feats = np.zeros(6)
    email_addr_feats = np.zeros(8)

    fused = np.concatenate([email_text_feats, url_feats, email_addr_feats])

    prob = classify_phishing(fused)
    classification = 'Phishing Website' if prob > 0.5 else 'Safe Website'

    try:
        shap_categories = shap_top.explain_top_features_by_category(fused, top_k=5)
    except Exception as e:
        print(f"SHAP explanation failed: {e}")
        shap_categories = {'email_text': {}, 'url': {}, 'email_address': {}}

    
    # Generate reasoning from URL features only (email features are zeroed out)
    url_shap = shap_categories['url']
    reasoning = generate_reasoning('', url, '', classification, prob, url_shap)
    
    # Calculate risk score
    risk_score = calculate_risk_score(prob, url_shap, '', url)

    return jsonify({
        'probability': float(prob),
        'classification': classification,
        'confidence_label': f"{(prob * 100):.1f}%",
        'top_url_features': url_shap,
        'reasoning': reasoning,
        'risk_score': risk_score
    })

@app.route('/')
def index():
    return send_from_directory('../frontend', 'index.html')

if __name__ == '__main__':
    app.run(debug=True)