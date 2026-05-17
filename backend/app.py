from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from typing import Dict
import xgboost as xgb
import numpy as np
import re
import os
import joblib
import warnings

warnings.filterwarnings('ignore')

from gmail_api import (
    build_gmail_service,
    list_unread_messages,
    get_message_payload,
    extract_email_body
)

from feature_extraction import (
    extract_email_text_features,
    extract_urls,
    extract_url_features,
    extract_email_address_features,
    fuse_features,
)
<<<<<<< HEAD
from settings import MODEL_PATHS
from model_ensemble import EnsembleClassifier
from shap_explainer import SHAPTopFeatures
from db import init_db
from gmail_processor import process_unread_messages
from gmail_api import build_gmail_service

=======
>>>>>>> 46a602902786e0a0088d4d8af230ec9289081e9a

from settings import MODEL_PATHS, FEATURE_DIMENSIONS

app = Flask(__name__, static_folder='../frontend')

<<<<<<< HEAD
# Enable CORS with flask-cors for Chrome extension support
CORS(app, supports_credentials=False)


# Load model
script_dir = os.path.dirname(os.path.abspath(__file__))
=======
# =====================================================
# CORS
# =====================================================

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    return response

>>>>>>> 46a602902786e0a0088d4d8af230ec9289081e9a

# =====================================================
# LOAD MODEL
# =====================================================

print("Loading model...")

xgb_model = xgb.XGBClassifier()

xgb_model.load_model(MODEL_PATHS['xgb'])

scaler = joblib.load(MODEL_PATHS['scaler'])

model = xgb_model

print("Model loaded successfully!")


# =====================================================
# HELPERS
# =====================================================

def clean_email_text(text):
    text = re.sub(r'\\s+', ' ', str(text))
    return text.strip()


def safe_vector(arr, size):
    arr = np.array(arr, dtype=float).flatten()

    if len(arr) < size:
        arr = np.concatenate([arr, np.zeros(size - len(arr))])

    elif len(arr) > size:
        arr = arr[:size]

    return arr


def classify_phishing(features):
    features = np.array(features, dtype=float).reshape(1, -1)

    features_scaled = scaler.transform(features)

    prob = model.predict_proba(features_scaled)[0][1]

    return float(prob)


# =====================================================
# ROUTES
<<<<<<< HEAD
# -----------------------------

@app.route('/classify', methods=['POST', 'OPTIONS'])
def classify():
    """Single email classifier endpoint for the Gmail extension."""
    if request.method == 'OPTIONS':
        return '', 204
    data = request.json or {}

    email_text = clean_email_text(data.get('email_text', ''))
    email_address = data.get('email_address', '')

    email_text_feats = extract_email_text_features(email_text)
    urls = extract_urls(email_text)
    url_features = [extract_url_features(u) for u in urls]
    email_addr_feats = extract_email_address_features(email_address)

    fused = fuse_features(email_text_feats, url_features, email_addr_feats)

    prob = classify_phishing(fused)
    classification = 'Phishing' if prob > 0.7 else 'Legitimate'

    top_by_cat = shap_helper.explain_top_features_by_category(fused)
    url_from_email = urls[0] if urls else ''
    all_top = {
        **top_by_cat.get('email_text', {}),
        **top_by_cat.get('url', {}),
        **top_by_cat.get('email_address', {}),
    }

    reasoning = generate_reasoning(email_text, url_from_email, email_address, classification, prob, all_top)
    risk_score = calculate_risk_score(prob, all_top, email_text, url_from_email)

    return jsonify({
        'probability': float(prob),
        'classification': classification,
        'confidence_label': f"{(prob * 100):.1f}%",
        'reasoning': reasoning,
        'risk_score': risk_score,
        'top_email_features': top_by_cat.get('email_text', {}),
        'top_url_features': top_by_cat.get('url', {}),
        'top_email_address_features': top_by_cat.get('email_address', {}),
    })


@app.route('/predict', methods=['POST', 'OPTIONS'])
def predict():
    if request.method == 'OPTIONS':
        return '', 204
    data = request.json


    email_text = clean_email_text(data.get('email_text', ''))
    text_lower = email_text.lower()

    suspicious_words = ['click', 'verify', 'password', 'login', 'pay', 'urgent']

    # Processing all emails without early return to ensure SHAP features are generated
    email_address = data.get('email_address', '')

    email_text_feats = extract_email_text_features(email_text)

    urls = extract_urls(email_text)
    url_features = [extract_url_features(url) for url in urls]

    email_addr_feats = extract_email_address_features(email_address)

    fused = fuse_features(email_text_feats, url_features, email_addr_feats)

    prob = classify_phishing(fused)
    classification = 'Phishing' if prob > 0.7 else 'Legitimate'

    # SHAP/top-feature explanation (robust + no random placeholders)
    top_by_cat = shap_helper.explain_top_features_by_category(fused)

    # Generate reasoning from all top features combined
    url_from_email = urls[0] if urls else ''
    all_top = {
        **top_by_cat.get('email_text', {}),
        **top_by_cat.get('url', {}),
        **top_by_cat.get('email_address', {}),
    }
    reasoning = generate_reasoning(email_text, url_from_email, email_address, classification, prob, all_top)

    
    # Calculate risk score
    risk_score = calculate_risk_score(prob, all_top, email_text, url_from_email)


    return jsonify({
        'probability': float(prob),
        'classification': classification,
        'confidence_label': f"{(prob * 100):.1f}%",
        'top_email_features': top_by_cat.get('email_text', {}),
        'top_url_features': top_by_cat.get('url', {}),
        'top_email_address_features': top_by_cat.get('email_address', {}),
        'reasoning': reasoning,
        'risk_score': risk_score,
        'ensemble_breakdown': getattr(model, 'last_votes', {}),
        'model_version': getattr(model, 'version', 'v1.0')
    })

@app.route('/predict_url', methods=['POST', 'OPTIONS'])
def predict_url():
    if request.method == 'OPTIONS':
        return '', 204
    data = request.json
    url = data.get('url', '')

    # Extract URL features
    url_feats = extract_url_features(url)

    # Empty email + sender features (to match model input size)
    email_text_feats = np.zeros(13)
    email_addr_feats = np.zeros(8)

    fused = np.concatenate([email_text_feats, url_feats, email_addr_feats])

    prob = classify_phishing(fused)
    classification = 'Phishing Website' if prob > 0.5 else 'Safe Website'

    top_by_cat = shap_helper.explain_top_features_by_category(fused)
    url_shap = top_by_cat.get('url', {})

    # Generate reasoning from URL features only (email features are zeroed out)
    reasoning = generate_reasoning('', url, '', classification, prob, url_shap)
    
    # Calculate risk score
    risk_score = calculate_risk_score(prob, url_shap, '', url)

    return jsonify({
        'probability': float(prob),
        'classification': classification,
        'confidence_label': f"{(prob * 100):.1f}%",
        'top_url_features': url_shap,
        'reasoning': reasoning,
        'risk_score': risk_score,
        'ensemble_breakdown': getattr(model, 'last_votes', {}),
        'model_version': getattr(model, 'version', 'v1.0')
    })
=======
# =====================================================
>>>>>>> 46a602902786e0a0088d4d8af230ec9289081e9a

@app.route('/')
def index():
    return send_from_directory('../frontend', 'index.html')

<<<<<<< HEAD
@app.route('/gmail/unread_count', methods=['GET'])
def gmail_unread_count():
    """Return number of unread Gmail messages (best-effort)."""
    try:
        service = build_gmail_service()
        unread = service.users().messages().list(userId='me', labelIds=['UNREAD'], maxResults=1).execute()
        # Gmail returns only a page; 'resultSizeEstimate' is best-effort.
        count = unread.get('resultSizeEstimate', 0) if isinstance(unread, dict) else 0
        return jsonify({'unread_count': int(count)})
    except Exception as e:
        return jsonify({'unread_count': 0, 'error': str(e)}), 500


@app.route('/gmail/process_once', methods=['POST'])
def gmail_process_once():
    """Process unread Gmail messages and log results to SQLite."""
    data = request.json or {}
    max_messages = int(data.get('max_messages', 10))

    # Build Gmail service (OAuth); requires credentials.json in runtime dir
    service = build_gmail_service()

    def classify_fn(email_text: str, email_address: str) -> Dict[str, object]:
        email_text = clean_email_text(email_text or '')

        email_text_feats = extract_email_text_features(email_text)
        urls = extract_urls(email_text)
        url_features = [extract_url_features(u) for u in urls]
        email_addr_feats = extract_email_address_features(email_address or '')

        fused = fuse_features(email_text_feats, url_features, email_addr_feats)
        prob = classify_phishing(fused)
        classification = 'Phishing' if prob > 0.7 else 'Legitimate'

        top_by_cat = shap_helper.explain_top_features_by_category(fused)
        url_from_email = urls[0] if urls else ''
        all_top = {
            **top_by_cat.get('email_text', {}),
            **top_by_cat.get('url', {}),
            **top_by_cat.get('email_address', {}),
        }
        reasoning = generate_reasoning(email_text, url_from_email, email_address or '', classification, prob, all_top)
        risk_score = calculate_risk_score(prob, all_top, email_text, url_from_email)

        return {
            'probability': float(prob),
            'classification': classification,
            'reasoning': reasoning,
            'risk_score': risk_score,
        }

    results = process_unread_messages(
        service=service,
        classify_fn=classify_fn,
        db_path=None,
        max_messages=max_messages,
    )

    return jsonify({'processed': len(results), 'results': results})


if __name__ == '__main__':
    app.run(debug=True)

=======

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok'
    })


# =====================================================
# EMAIL PREDICTION
# =====================================================

@app.route('/predict', methods=['POST'])
@app.route('/predict', methods=['POST'])
def predict():

    try:

        data = request.json

        email_text = clean_email_text(
            data.get('email_text', '')
        )

        email_address = data.get(
            'email_address',
            ''
        )

        # ---------------------------------------------
        # BASIC VALIDATION
        # ---------------------------------------------

        if not email_text.strip():

            return jsonify({
                'error': 'Please enter email content.'
            }), 400

        # ---------------------------------------------
        # FEATURE EXTRACTION
        # ---------------------------------------------

        email_feats = safe_vector(
            extract_email_text_features(email_text),
            FEATURE_DIMENSIONS['email_text']
        )

        urls = extract_urls(email_text)

        url_feature_list = []

        for u in urls:

            try:

                url_feature_list.append(
                    safe_vector(
                        extract_url_features(u),
                        FEATURE_DIMENSIONS['url']
                    )
                )

            except:
                continue

        if url_feature_list:

            url_feats = np.mean(
                url_feature_list,
                axis=0
            )

        else:

            url_feats = np.zeros(
                FEATURE_DIMENSIONS['url']
            )

        email_addr_feats = safe_vector(
            extract_email_address_features(email_address),
            FEATURE_DIMENSIONS['email_address']
        )

        fused = np.concatenate([
            email_feats,
            url_feats,
            email_addr_feats
        ])

        # ---------------------------------------------
        # MODEL PREDICTION
        # ---------------------------------------------

        prob = classify_phishing(fused)

        raw_score = round(prob * 100, 1)

        # ---------------------------------------------
        # CLASSIFICATION LOGIC
        # ---------------------------------------------

        if raw_score >= 95:

            classification = 'Phishing'

        elif raw_score >= 85:

            classification = 'Suspicious'

        else:

            classification = 'Legitimate'

        # ---------------------------------------------
        # DISPLAY RISK SCORE
        # ---------------------------------------------

        display_score = raw_score

        # Short email calibration
        if len(email_text.strip()) < 5:

            display_score = min(display_score, 45)

        elif len(email_text.strip()) < 15:

            display_score = min(display_score, 55)

        # UI consistency calibration
        if classification == 'Legitimate':

            display_score = min(display_score, 35)
            risk_level = 'Low'

        elif classification == 'Suspicious':

            display_score = max(
                min(display_score, 75),
                45
            )

            risk_level = 'Medium'

        else:

            display_score = max(display_score, 85)
            risk_level = 'High'

        # ---------------------------------------------
        # REASONING
        # ---------------------------------------------

        if len(email_text.strip()) < 15:

            reasoning = (
                'Short email detected. '
                'Prediction confidence may be lower.'
            )

        elif classification == 'Phishing':

            reasoning = (
                'Potential phishing indicators detected.'
            )

        elif classification == 'Suspicious':

            reasoning = (
                'Some suspicious linguistic or URL patterns detected.'
            )

        else:

            reasoning = (
                'Content appears legitimate.'
            )

        # ---------------------------------------------
        # RESPONSE
        # ---------------------------------------------

        return jsonify({

            'probability': prob,

            'classification': classification,

            'risk_score': display_score,

            'risk_level': risk_level,

            'confidence_label': f'{display_score:.1f}%',

            'top_email_features': {},

            'top_url_features': {},

            'top_email_address_features': {},

            'reasoning': reasoning,

            'ensemble_breakdown': {},

            'model_version': 'v2-stable'
        })

    except Exception as e:

        print("PREDICT ERROR:", str(e))

        return jsonify({
            'error': str(e)
        }), 500

# =====================================================
# URL PREDICTION
# =====================================================

@app.route('/predict_url', methods=['POST'])
def predict_url():

    try:

        data = request.json

        url = str(data.get('url', '')).strip()

        trusted_domains = [
            'google.com',
            'youtube.com',
            'microsoft.com',
            'github.com',
            'openai.com',
            'amazon.com',
            'paypal.com',
            'apple.com',
            'facebook.com',
            'instagram.com',
            'linkedin.com',
            'wikipedia.org'
        ]

        for domain in trusted_domains:

            if domain in url.lower():

                return jsonify({

                    'probability': 0.01,

                    'classification': 'Safe Website',

                    'risk_score': 1,

                    'confidence_label': '99%',

                    'top_url_features': {},

                    'reasoning':
                        'Trusted domain detected.',

                    'ensemble_breakdown': {},

                    'model_version': 'v2-stable'
                })

        if len(url) < 3:
            return jsonify({
                'error': 'Invalid URL'
            }), 400

        url_feats = safe_vector(
            extract_url_features(url),
            FEATURE_DIMENSIONS['url']
        )

        email_feats = np.zeros(
            FEATURE_DIMENSIONS['email_text']
        )

        email_addr_feats = np.zeros(
            FEATURE_DIMENSIONS['email_address']
        )

        fused = np.concatenate([
            email_feats,
            url_feats,
            email_addr_feats
        ])

        prob = classify_phishing(fused)

        classification = (
            'Phishing Website'
            if prob > 0.85
            else 'Safe Website'
        )

        risk_score = round(prob * 100, 1)

        return jsonify({
            'probability': prob,
            'classification': classification,
            'risk_score': risk_score,
            'confidence_label': f'{risk_score:.1f}%',

            'top_url_features': {},

            'reasoning': (
                'Suspicious URL patterns detected.'
                if classification == 'Phishing Website'
                else 'Website appears safe.'
            ),

            'ensemble_breakdown': {},
            'model_version': 'v2-stable'
        })

    except Exception as e:

        print("URL PREDICT ERROR:", str(e))

        return jsonify({
            'error': str(e)
        }), 500


# =====================================================
# START SERVER
# =====================================================

@app.route('/scan_gmail', methods=['GET'])
def scan_gmail():

    try:

        service = build_gmail_service(
            credentials_path='credentials.json'
        )

        messages = list_unread_messages(
            service,
            max_results=10
        )

        results = []

        for msg in messages:

            payload = get_message_payload(
                service,
                msg['id']
            )

            email_body = extract_email_body(payload)

            if not email_body:
                continue

            email_feats = safe_vector(
                extract_email_text_features(email_body),
                FEATURE_DIMENSIONS['email_text']
            )

            urls = extract_urls(email_body)

            url_feature_list = []

            for u in urls:

                try:

                    url_feature_list.append(
                        safe_vector(
                            extract_url_features(u),
                            FEATURE_DIMENSIONS['url']
                        )
                    )

                except:
                    continue

            if url_feature_list:

                url_feats = np.mean(
                    url_feature_list,
                    axis=0
                )

            else:

                url_feats = np.zeros(
                    FEATURE_DIMENSIONS['url']
                )

            email_addr_feats = np.zeros(
                FEATURE_DIMENSIONS['email_address']
            )

            fused = np.concatenate([
                email_feats,
                url_feats,
                email_addr_feats
            ])

            prob = classify_phishing(fused)

            if prob > 0.95:
                classification = 'Phishing'
                color = '#dc3545'

            elif prob > 0.9:
                classification = 'Suspicious'
                color = '#ffc107'

            else:
                classification = 'Legitimate'
                color = '#28a745'

            results.append({
                'snippet': (
                    email_body
                    .replace('\n', '<br>')
                    .replace('\r', '')
                    .strip()[:250]
                ),
                'classification': classification,
                'probability': round(prob * 100, 2),
                'color': color
            })

        # ============================================
        # BUILD HTML UI
        # ============================================

        html = """

        <html>

        <head>

        <title>PhishGuard Gmail Scan</title>

        <style>

        body{
            font-family:Arial;
            background:#0f172a;
            color:white;
            padding:30px;
        }

        h1{
            text-align:center;
            margin-bottom:40px;
        }

        .card{
            background:#1e293b;
            padding:20px;
            border-radius:12px;
            margin-bottom:20px;
            box-shadow:0 0 10px rgba(0,0,0,0.4);
        }

        .badge{
            padding:6px 14px;
            border-radius:8px;
            color:white;
            font-weight:bold;
            display:inline-block;
            margin-bottom:10px;
        }

        .prob{
            margin-top:10px;
            font-size:18px;
        }

        .snippet{
            margin-top:15px;
            line-height:1.6;
            color:#d1d5db;
            white-space:pre-wrap;
        }

        </style>

        </head>

        <body>

        <h1>📧 Gmail Inbox Scan Results</h1>

        """

        phishing_count = 0
        suspicious_count = 0
        legit_count = 0

        for r in results:

            if r['classification'] == 'Phishing':
                phishing_count += 1

            elif r['classification'] == 'Suspicious':
                suspicious_count += 1

            else:
                legit_count += 1

            html += f"""

            <div class="card">

                <div
                    class="badge"
                    style="background:{r['color']};"
                >
                    {r['classification']}
                </div>

                <div class="prob">
                    Risk Score:
                    {r['probability']}%
                </div>

                <div class="snippet">
                    {r['snippet']}
                </div>

            </div>

            """

        html = f"""

        <div style="
            display:flex;
            gap:20px;
            margin-bottom:40px;
            justify-content:center;
        ">

            <div class="card">
                ✅ Legitimate: {legit_count}
            </div>

            <div class="card">
                ⚠ Suspicious: {suspicious_count}
            </div>

            <div class="card">
                🚨 Phishing: {phishing_count}
            </div>

        </div>

        """ + html

        html += """

        </body>
        </html>

        """

        return html

    except Exception as e:

        print("GMAIL SCAN ERROR:", str(e))

        return f"""

        <h1>Gmail Scan Error</h1>

        <p>{str(e)}</p>

        """

if __name__ == '__main__':

    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )
