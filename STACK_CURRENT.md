# What Happens Here + Current Tech Stack

This document describes what the project currently does end-to-end and the tech stack used by the existing codebase.

---

## High-level flow (what happens at runtime)

1. **Frontend (browser UI)**
   - `frontend/index.html` provides a simple UI.
   - It sends user input to the backend (either **email text + email address** or **a URL-only** request).

2. **Backend API (Flask)**
   - `backend/app.py` runs the HTTP endpoints.
   - On startup it loads the trained ML artifacts:
     - `xgb_model.json` (baseline XGBoost)
     - plus an optional ensemble model/scaler if present (see `backend/settings.py`).

3. **Feature extraction**
   - `backend/feature_extraction.py` contains shared feature logic.
   - `backend/extract_email_address_features.py` computes sender/email-address-related features.
   - Feature extraction is reused by both training and prediction.

4. **Prediction (ML models / ensemble)**
   - The backend predicts phishing vs legitimate using the trained model(s).
   - The repo is built around a multi-model ensemble concept (XGBoost / RandomForest / LightGBM), with voting/combination logic implemented in the ensemble-related modules.

5. **Explainability (SHAP)
   - `backend/shap_explainer.py` provides SHAP-based explanation utilities.
   - `backend/app.py` includes defensive handling so the endpoint still returns sensible output when SHAP values are empty or have unexpected shapes.

6. **Response returned to frontend**
   - Endpoints return JSON including:
     - classification label
     - probability/confidence
     - risk score
     - “top features” breakdown for interpretability
     - reasoning text (LLM reasoning is part of the design; actual invocation depends on how endpoints are wired in `app.py`).

---

## What happens for training (offline)

1. **Baseline training (XGBoost)**
   - `backend/train.py` trains the primary XGBoost model.
   - Saves:
     - `backend/xgb_model.json`
     - `backend/scaler.pkl`

2. **Optional ensemble training**
   - `backend/ensemble_train.py` trains a multi-model ensemble.
   - Produces ensemble artifacts referenced from `backend/settings.py` (e.g., `ensemble_model.pkl`) and updates scaler usage.

---

## Current tech stack

### Language & runtime
- **Python** (backend + training)

### Backend web framework
- **Flask** (`backend/app.py`)

### ML / data processing
- **NumPy**
- **Pandas**
- **scikit-learn**
- **XGBoost**
- **LightGBM** (used for ensemble when available)
- **joblib** (artifact serialization)

### Explainability
- **SHAP**

### NLP / LLM components (present in repo)
- **transformers**
- **torch**
- **sentence-transformers**
- **Ollama / LLM reasoning modules**
  - `backend/llm_reasoning_ollama.py`
  - (Used to generate natural-language reasoning; whether it is invoked on every request depends on `backend/app.py` wiring.)

### Email / integrations (present in repo)
- **Google Gmail API**
  - `backend/gmail_api.py`
  - OAuth modules are included in `requirements.txt`

### Async/background tasks (present in repo)
- **Celery** (`backend/task_queue.py`)
- **Redis**

### Vector database (present in repo)
- **FAISS** (`backend/vector_store.py`)

### Frontend
- Plain **HTML** UI
- **Plotly** (`frontend/plotly.min.js`)

### Dependencies
- Defined in `requirements.txt`

---

## Key repository modules (by responsibility)

- `backend/app.py`: Flask routes, prediction orchestration, response formatting.
- `backend/settings.py`: central paths/config (model/data locations).
- `backend/feature_extraction.py`: shared phishing feature extraction.
- `backend/extract_email_address_features.py`: sender/address-specific features.
- `backend/train.py`: baseline training (XGBoost).
- `backend/ensemble_train.py`, `backend/model_ensemble.py`: ensemble training/inference helpers.
- `backend/shap_explainer.py`: SHAP utilities.
- `backend/llm_reasoning_ollama.py`: LLM reasoning utilities.
- `backend/gmail_api.py`: Gmail access/integration utilities.
- `backend/task_queue.py`: Celery/Redis task queue helpers.
- `backend/vector_store.py`: FAISS vector store utilities.

---

## Artifacts produced / used

- `backend/xgb_model.json` (XGBoost model)
- `backend/scaler.pkl` (feature scaler)
- (Optional) ensemble artifacts referenced by `backend/settings.py` (e.g., `ensemble_model.pkl`)

---

## Where to look next in code

- Start with **`backend/app.py`** to see the exact request/response contract and which modules are invoked per endpoint.
- Then check **`backend/feature_extraction.py`** and **`backend/extract_email_address_features.py`** for the exact feature set.
- Finally review **`backend/train.py`** and **`backend/ensemble_train.py`** to confirm how the training pipeline matches inference.

