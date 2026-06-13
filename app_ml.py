import streamlit as st
import joblib
import pandas as pd
from utils.feature_extractor import extract_features
from scipy.sparse import hstack, csr_matrix

model = joblib.load('models/hybrid_model.pkl')
vectorizer = joblib.load('models/tfidf_vectorizer.pkl')

def predict(text):
    struct = extract_features(text)
    struct_arr = [[struct['amount'], struct['date_consistent'], struct['length_of_stay'],
                   struct['amount_deviation'], struct['treatment_match']]]
    X_struct = csr_matrix(struct_arr)
    X_text = vectorizer.transform([text])
    X_combined = hstack([X_text, X_struct])
    proba = model.predict_proba(X_combined)[0]
    pred = model.predict(X_combined)[0]
    confidence = proba[1] if pred == 1 else proba[0]
    verdict = "SUSPICIOUS" if pred == 1 else "GENUINE"
    return verdict, confidence, struct

# Streamlit UI (similar to before)
st.title("Medical Forgery Detector (Hybrid ML)")
uploaded = st.file_uploader("Upload .txt", type=['txt'])
if uploaded:
    text = uploaded.read().decode('utf-8')
    verdict, conf, feats = predict(text)
    st.metric("Verdict", verdict)
    st.metric("Confidence", f"{conf:.2f}")
    st.json(feats)