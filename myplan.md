PhishGuard 3.0 - Real-time Gmail Integration System
Basic outline for the project
📋 Updated Tech Stack (100% Free)
Component	Technology	Purpose
Email Integration	Gmail API (OAuth 2.0)	Real-time email access
ML Models	XGBoost, Random Forest, LightGBM, DistilBERT	Multi-algorithm ensemble
LLM for Analysis	Ollama + Llama 3 (8B)	Natural language reasoning
Feature Extraction	Custom Python + transformers	URL, header, content analysis
Vector Database	FAISS (Facebook)	Fast similarity search
Task Queue	Celery + Redis	Async processing
Database	SQLite (lightweight)	Store predictions & feedback
Dashboard	Flask + Plotly + Chart.js	Visualization
Deployment	Ngrok (free tunnel)	Testing Gmail webhook

Multi-Model Ensemble System
Focus: Build and compare multiple ML algorithms

Tasks (Conceptual)
1.	Implement 3 parallel models:
	o	XGBoost (baseline)
	o	Random Forest (interpretable)
	o	LightGBM (fast training when available)
2.	Create ensemble voting system (soft/hard voting; soft is preferred)
3.	Extract 50+ phishing features:
	o	URL features (length, subdomains, special chars)
	o	Content features (urgency words, grammar errors, suspicious intent keywords)
	o	Header/sender features (reply-to mismatches, missing/auth signals when available)
4.	Train on existing dataset (optionally expand with PhishTank)
5.	Implement model versioning and A/B testing

Execution (Run it step-by-step as the project is currently wired)

0) Prerequisites (do once)
1.	Install dependencies from repo root:
		pip install -r requirements.txt
2.	Make sure you have the dataset CSVs in `dataset/` (used by ensemble_train.py).

A) Train the ensemble + scaler (required if models are missing)
1.	From repo root (d:/PhishGaurd2.0), run:
		python backend/ensemble_train.py
2.	Verify that model artifacts were created (the script saves to paths in `backend/settings.py`).

B) Start the API server (runtime)
1.	From repo root, run:
		python backend/app.py
2.	Open the server output to find the local URL (Flask usually starts on http://127.0.0.1:5000).

C) Test predictions
1.	POST /predict (email analysis)
	- URL: http://127.0.0.1:5000/predict
	- Body (JSON example):
		{
		  "email_text": "<paste email body text>",
		  "email_address": "user@example.com"
		}
2.	POST /predict_url (URL-only analysis)
	- URL: http://127.0.0.1:5000/predict_url
	- Body (JSON example):
		{
		  "url": "https://example.com/login"
		}
3.	Both endpoints return:
	- probability + classification
	- top_email_features / top_url_features / top_email_address_features
	- reasoning and risk_score

Notes
- The app loads the ensemble model + scaler at startup (see `backend/app.py`). If the model/scaler files are missing, it will fall back to the XGBoost baseline or error depending on what artifacts exist in `backend/settings.py`.

Output
- ensemble model + scaler artifacts
- working feature extraction is provided by backend/feature_extraction.py and referenced throughout the ensemble training + app routes
