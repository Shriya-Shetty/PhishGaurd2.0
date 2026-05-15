# 🛡️ PhishGuard

PhishGuard is a machine learning-based phishing detection application. It extracts email, URL, sender, and header features, then classifies content as phishing or legitimate.

---

## 🚀 Features

* 🔍 Phishing detection using ML models
* 📊 Shared feature extraction module for email, URL, and sender data
* 🧠 Optional ensemble training with XGBoost, Random Forest, and LightGBM
* 🌐 Flask backend with frontend test interface
* 🔄 Centralized backend settings and model path configuration

---

## 🏗️ Project Structure

```
PhishGuard/
│
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
│   └── scaler.pkl
├── frontend/
│   ├── index.html
│   └── plotly.min.js
├── dataset/
│   ├── CEAS_08.csv
│   ├── urldata.csv
│   └── dataset_phishtank.csv
├── requirements.txt
└── README.md
```

---

## ⚙️ How It Works

1. Frontend sends a URL or email text to the backend
2. `backend/app.py` loads the model and extracts features
3. The model predicts phishing probability
4. Results include classification, confidence, risk score, and reasoning

---

## 🧪 Setup & Installation

### 1. Clone the repository

```bash
git clone <repo-url>
cd PhishGaurd1.0
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 🔧 Training

### Train baseline XGBoost model

```bash
python backend/train.py
```

This generates:

* `backend/xgb_model.json`
* `backend/scaler.pkl`

### Train optional ensemble model

```bash
python backend/ensemble_train.py
```

This generates:

* `backend/ensemble_model.pkl`
* `backend/scaler.pkl`

---

## ▶️ Run the backend server

```bash
python backend/app.py
```

Then open `frontend/index.html` in your browser or visit `http://localhost:5000` if the frontend is served from Flask.

---

## 📊 Datasets

The current repo includes CSV dataset placeholders under `dataset/`.

Use your own phishing datasets or download from:

* PhishTank
* Kaggle phishing datasets

---

## 🛠️ Notes

* `backend/app.py` loads the ensemble model automatically if `backend/ensemble_model.pkl` exists.
* `backend/settings.py` centralizes dataset and model file paths.
* `backend/feature_extraction.py` contains shared feature logic used by training and prediction.

---

## 📌 Future Improvements

* Gmail webhook integration
* Celery async task queue support
* FAISS vector store for similarity search
* Model versioning and A/B testing

---

## 📄 License

This project is open-source and available under the MIT License.
