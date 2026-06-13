import os
import joblib
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from scipy.sparse import hstack
from utils.feature_extractor import extract_features

def load_data(genuine_dir, forged_dir):
    texts, labels, struct_feats = [], [], []
    for fname in os.listdir(genuine_dir):
        with open(os.path.join(genuine_dir, fname), 'r', encoding='utf-8') as f:
            text = f.read()
            texts.append(text)
            labels.append(0)
            feats = extract_features(text)
            struct_feats.append([feats['amount'], feats['date_consistent'], feats['length_of_stay'],
                                 feats['amount_deviation'], feats['treatment_match']])
    for fname in os.listdir(forged_dir):
        with open(os.path.join(forged_dir, fname), 'r', encoding='utf-8') as f:
            text = f.read()
            texts.append(text)
            labels.append(1)
            feats = extract_features(text)
            struct_feats.append([feats['amount'], feats['date_consistent'], feats['length_of_stay'],
                                 feats['amount_deviation'], feats['treatment_match']])
    return texts, labels, np.array(struct_feats)

print("Loading data...")
X_text, y, X_struct = load_data('data/genuine', 'data/forged')
print(f"Samples: {len(X_text)} (genuine: {y.count(0)}, forged: {y.count(1)})")

print("Vectorizing text...")
vectorizer = TfidfVectorizer(max_features=2000, ngram_range=(1,2), stop_words='english')
X_tfidf = vectorizer.fit_transform(X_text)

print("Combining features...")
from scipy.sparse import csr_matrix
X_struct_sparse = csr_matrix(X_struct)  # convert to sparse
X_combined = hstack([X_tfidf, X_struct_sparse])

X_train, X_test, y_train, y_test = train_test_split(X_combined, y, test_size=0.2, random_state=42, stratify=y)

print("Training Random Forest...")
rf = RandomForestClassifier(n_estimators=200, max_depth=20, min_samples_split=5, class_weight='balanced', random_state=42, n_jobs=-1)
rf.fit(X_train, y_train)

y_pred = rf.predict(X_test)
print(classification_report(y_test, y_pred))
print(confusion_matrix(y_test, y_pred))

cv_scores = cross_val_score(rf, X_combined, y, cv=5, scoring='accuracy')
print(f"5-fold CV accuracy: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

os.makedirs('models', exist_ok=True)
joblib.dump(rf, 'models/hybrid_model.pkl')
joblib.dump(vectorizer, 'models/tfidf_vectorizer.pkl')
joblib.dump(extract_features, 'models/feature_extractor.pkl')
print("Hybrid model saved.")