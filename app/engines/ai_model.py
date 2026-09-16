import numpy as np
import os
import pickle
from sklearn.ensemble import RandomForestClassifier

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "fraud_rf_model.pkl")

def get_or_train_model():
    if os.path.exists(MODEL_PATH):
        with open(MODEL_PATH, 'rb') as f:
            return pickle.load(f)
            
    # Dummy training data for hackathon MVP
    # Features: [num_dates, num_amounts, num_names, num_orgs, text_length]
    X_train = []
    y_train = []
    
    # Generate fake "authentic" documents (have many structured fields)
    for _ in range(500):
        X_train.append([
            np.random.randint(1, 4),  # dates
            np.random.randint(1, 10), # amounts
            np.random.randint(1, 3),  # names
            np.random.randint(1, 3),  # orgs
            np.random.randint(100, 1000) # text len
        ])
        y_train.append(0) # 0 = Authentic/Low Risk
        
    # Generate fake "fraud/tampered" documents (lacking structure, empty, or highly irregular)
    for _ in range(500):
        X_train.append([
            np.random.randint(0, 2),  # dates
            np.random.randint(0, 2),  # amounts
            np.random.randint(0, 1),  # names
            np.random.randint(0, 1),  # orgs
            np.random.randint(0, 200) # text len
        ])
        y_train.append(1) # 1 = Fraudulent/High Risk
        
    clf = RandomForestClassifier(n_estimators=50, random_state=42)
    clf.fit(X_train, y_train)
    
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(clf, f)
        
    return clf

def calculate_ai_risk_score(extracted_data: dict) -> tuple[int, list]:
    clf = get_or_train_model()
    
    num_dates = len(extracted_data.get('dates', []))
    num_amounts = len(extracted_data.get('amounts', []))
    num_names = len(extracted_data.get('names', []))
    num_orgs = len(extracted_data.get('organizations', []))
    text_length = len(extracted_data.get('raw_text', ''))
    
    features = [[num_dates, num_amounts, num_names, num_orgs, text_length]]
    
    # Get probability of class 1 (Fraud/High Risk)
    risk_prob = clf.predict_proba(features)[0][1]
    
    risk_score = int(risk_prob * 40) # Max 40 points from AI
    
    reasons = []
    if risk_score > 20:
        reasons.append(f"AI Model Analysis: High probability of irregular document structure ({risk_prob*100:.1f}% AI Risk Confidence).")
        
    return risk_score, reasons
