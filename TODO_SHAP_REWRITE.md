# TODO_SHAP_REWRITE

- [ ] Add `backend/shap_explainer.py`:
  - [ ] Cache SHAP explainer per process
  - [ ] Implement `explain_top_features_by_category(...)` returning stable `{email_text,url,email_address}`
  - [ ] Robustly pick phishing-positive class SHAP values
  - [ ] Fallback to perturbation importance if SHAP fails
  - [ ] Avoid hard-coded feature index ranges; derive category boundaries from feature lengths
- [ ] Edit `backend/app.py`:
  - [ ] Remove/replace `get_shap_by_category` and `_native_feature_importance`
  - [ ] Wire `/predict` and `/predict_url` to use new module
  - [ ] Ensure response JSON keys expected by frontend remain unchanged
- [ ] Quick sanity test commands (manual/run):
  - [ ] Run Flask and call `/predict` and `/predict_url`
  - [ ] Confirm top feature dicts populate and frontend charts render

