# PhishGuard Run Guide

This guide will help you set up and run the PhishGuard phishing detection project.

---

## Prerequisites

- **Python 3.8+** installed
- **pip** package manager
- **8GB+ RAM** recommended for optional DistilBERT features

---

## Installation

1. **Navigate to the project directory:**
   ```powershell
   cd D:\PhishGaurd1.0
   ```

2. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

   Required packages include:
   - flask
   - numpy
   - pandas
   - scikit-learn
   - xgboost
   - joblib
   - shap
   - matplotlib
   - transformers
   - torch
   - sentence-transformers
   - lightgbm
   - celery
   - redis
   - google-api-python-client
   - google-auth-oauthlib
   - google-auth-httplib2
   - faiss-cpu

---

## Training the Model

### Train the baseline XGBoost model

```powershell
python backend/train.py
```

This will:
- Load datasets from `dataset/`
- Extract features using `backend/feature_extraction.py`
- Train an XGBoost model
- Save `backend/xgb_model.json`
- Save `backend/scaler.pkl`

### Train the optional ensemble model

```powershell
python backend/ensemble_train.py
```

This will:
- Train a voting ensemble of XGBoost, Random Forest, and LightGBM (if available)
- Save `backend/ensemble_model.pkl`
- Save or update `backend/scaler.pkl`

---

## Running the Web Application

Start the Flask backend server:

```powershell
python backend/app.py
```

The server will start at `http://localhost:5000`.

> **Note:** `backend/app.py` loads the ensemble model automatically if `backend/ensemble_model.pkl` exists.

### Gmail integration (read/unread polling + SQLite logging)

This project also includes a Gmail reader (OAuth) that processes **UNREAD** Gmail messages and logs results into SQLite.

#### 1) Ensure Gmail OAuth credentials exist
- The Gmail helper uses `credentials.json` by default.
- Place your Gmail OAuth client credentials file at: `backend/credentials.json` (or change `backend/gmail_api.py` defaults).

#### 2) Process unread messages
```powershell
# processes up to 10 unread messages by default
Invoke-RestMethod -Method Post -Uri http://localhost:5000/gmail/process_once -ContentType 'application/json' -Body '{"max_messages": 10}'
```

#### 3) Check unread count
```powershell
Invoke-RestMethod -Method Get -Uri http://localhost:5000/gmail/unread_count
```

#### 4) SQLite logs
- SQLite DB path: `backend/phishguard.db`
- Gmail + prediction logs stored in: `gmail_messages` table (linked to rows in `predictions`).


---

## Using the Application

1. Open your browser and navigate to:
   ```
   http://localhost:5000
   ```

2. Use the frontend interface or send POST requests to the backend endpoints.

3. Outputs include:
   - **Classification** (Phishing or Legitimate)
   - **Probability / Confidence**
   - **Risk Score**
   - **Feature explanations**
   - **AI reasoning**

---

## Project Structure

```
PhishGuard1.0/
├── backend/
│   ├── app.py
│   ├── train.py
│   ├── ensemble_train.py
│   ├── model_ensemble.py
│   ├── feature_extraction.py
│   ├── extract_email_address_features.py
│   ├── settings.py
│   ├── db.py
│   ├── task_queue.py
│   ├── vector_store.py
│   ├── xgb_model.json
│   ├── scaler.pkl
│   └── ensemble_model.pkl
├── frontend/
│   ├── index.html
│   └── plotly.min.js
├── dataset/
│   ├── CEAS_08.csv
│   ├── urldata.csv
│   └── dataset_phishtank.csv
├── requirements.txt
├── README.md
└── RUN_GUIDE.md
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| Model file not found | Run `python backend/train.py` first |
| `ensemble_model.pkl` missing | Run `python backend/ensemble_train.py` |
| Port 5000 in use | Change the port in `backend/app.py` or stop the other service |
| DistilBERT download slow | Allow a few minutes on first run |

---

## Quick Start Commands

```powershell
cd D:\PhishGaurd1.0
pip install -r requirements.txt
python backend/train.py
python backend/app.py
```
