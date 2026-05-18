from flask import Flask, jsonify, request, send_from_directory
import os, random

app = Flask(__name__)

FRONTEND = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))

@app.route('/')
def index():
    return send_from_directory(FRONTEND, 'index.html')

@app.route('/dashboard')
def dashboard():
    return send_from_directory(FRONTEND, 'dashboard.html')

@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json() or {}
    text = data.get('email_text', '')
    is_phish = any(w in text.lower() for w in ['click','urgent','verify','bank','password','win','suspend'])
    prob = round(random.uniform(0.72, 0.95) if is_phish else random.uniform(0.05, 0.28), 3)
    return jsonify({
        "classification": "Phishing" if is_phish else "Legitimate",
        "probability": prob,
        "confidence_label": "High Confidence",
        "risk_score": int(prob * 100),
        "reasoning": "Urgency words detected in subject. Sender domain does not match Reply-To. URL contains IP address instead of domain name.",
        "top_email_features": [
            ["urgency_words", 0.45], ["has_link", 0.38],
            ["exclamation_count", 0.22], ["caps_ratio", 0.18],
            ["suspicious_keywords", 0.15]
        ],
        "top_url_features": [
            ["url_length", 0.55], ["num_subdomains", 0.40],
            ["has_ip_address", 0.30], ["special_chars", 0.20]
        ],
        "top_email_address_features": []
    })

@app.route('/api/emails')
def api_emails():
    status = request.args.get('status', 'all')
    emails = [
        {"id":1,"sender_email":"noreply@paypa1.com","preview":"Urgent: Your account has been suspended. Click here to verify immediately.","classification":"Phishing","risk_score":91,"status":"processed","timestamp":"2025-05-16 10:22"},
        {"id":2,"sender_email":"team@github.com","preview":"Your pull request was merged successfully into main.","classification":"Legitimate","risk_score":8,"status":"processed","timestamp":"2025-05-16 10:18"},
        {"id":3,"sender_email":"alerts@amaz0n.co","preview":"You have won a $500 gift card! Claim it now before it expires tonight.","classification":"Phishing","risk_score":87,"status":"processed","timestamp":"2025-05-16 10:10"},
        {"id":4,"sender_email":"hr@company.com","preview":"Reminder: Please submit your timesheet by end of day Friday.","classification":"Legitimate","risk_score":5,"status":"processed","timestamp":"2025-05-16 09:55"},
        {"id":5,"sender_email":"support@unknown-bank.net","preview":"Verify your identity immediately to avoid permanent account closure.","classification":"Phishing","risk_score":94,"status":"pending","timestamp":"2025-05-16 09:40"},
        {"id":6,"sender_email":"no-reply@linkedin.com","preview":"You have 3 new connection requests waiting for your response.","classification":"Legitimate","risk_score":11,"status":"processed","timestamp":"2025-05-16 09:20"},
        {"id":7,"sender_email":"security@micros0ft.net","preview":"Your Microsoft account will be locked. Confirm your password now.","classification":"Phishing","risk_score":89,"status":"pending","timestamp":"2025-05-16 09:05"},
    ]
    if status != 'all':
        emails = [e for e in emails if e['status'] == status]
    return jsonify({"emails": emails, "count": len(emails)})

@app.route('/api/email/<int:email_id>')
def api_email_detail(email_id):
    emails = {
        1: {"id":1,"sender_email":"noreply@paypa1.com","email_text":"Urgent: Your account has been suspended. Click here to verify immediately.","classification":"Phishing","risk_score":91,"probability":0.91,"reasoning":"Sender domain paypa1.com is a typosquat of paypal.com. Email contains urgency words and a suspicious redirect URL.","top_email_features":[["urgency_words",0.45],["has_link",0.38],["caps_ratio",0.22]],"top_url_features":[["url_length",0.55],["has_ip_address",0.40]],"top_email_address_features":[]},
        2: {"id":2,"sender_email":"team@github.com","email_text":"Your pull request was merged successfully into main.","classification":"Legitimate","risk_score":8,"probability":0.08,"reasoning":"Sender is a known legitimate domain. No urgency words, no suspicious URLs detected.","top_email_features":[["urgency_words",0.02],["has_link",0.05]],"top_url_features":[["url_length",0.03]],"top_email_address_features":[]},
    }
    email = emails.get(email_id, {"id":email_id,"classification":"Phishing","risk_score":75,"probability":0.75,"reasoning":"Mock analysis.","top_email_features":[["urgency_words",0.4]],"top_url_features":[["url_length",0.3]],"top_email_address_features":[]})
    return jsonify(email)

@app.route('/api/metrics')
def api_metrics():
    return jsonify({
        "feedback": {"total": 23, "correct": 19, "accuracy": 82.6},
        "model": {
            "model_type": "Ensemble (XGBoost + Random Forest + LightGBM)",
            "last_trained": "2025-05-16 08:00",
            "model_size_kb": 842.3
        },
        "feedback_threshold": 100
    })

@app.route('/api/feedback', methods=['POST'])
def api_feedback():
    data = request.get_json() or {}
    fake_total = random.randint(24, 99)
    return jsonify({
        "success": True,
        "total_feedback": fake_total,
        "retraining_triggered": fake_total >= 100
    })

@app.route('/webhook/gmail', methods=['POST'])
def gmail_webhook():
    print("[Webhook] Gmail notification received")
    return 'OK', 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)