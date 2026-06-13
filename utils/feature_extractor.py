import re
from datetime import datetime

def extract_features(text):
    features = {}
    
    # 1. Extract fields using regex
    patient_name = re.search(r"Patient Name:\s*(.+)", text)
    patient_id = re.search(r"Patient ID:\s*(\S+)", text)
    admit_date = re.search(r"Admission Date:\s*(\S+)", text)
    discharge_date = re.search(r"Discharge Date:\s*(\S+)", text)
    diagnosis = re.search(r"Diagnosis:\s*(.+)", text)
    treatment = re.search(r"Treatment:\s*(.+)", text)
    amount = re.search(r"Total Amount:\s*₹([\d,]+)", text)
    hospital = re.search(r"Hospital:\s*(.+)", text)
    
    # 2. Numerical features
    amount_val = float(amount.group(1).replace(',', '')) if amount else 0
    features['amount'] = amount_val
    
    # 3. Date consistency (discharge >= admission)
    date_consistent = 1
    if admit_date and discharge_date:
        try:
            admit = datetime.strptime(admit_date.group(1), "%Y-%m-%d")
            discharge = datetime.strptime(discharge_date.group(1), "%Y-%m-%d")
            date_consistent = 1 if discharge >= admit else 0
        except:
            date_consistent = 0
    features['date_consistent'] = date_consistent
    
    # 4. Length of stay (in days)
    los = 0
    if admit_date and discharge_date and date_consistent:
        los = (discharge - admit).days
    features['length_of_stay'] = los
    
    # 5. Diagnosis-specific expected amount (from known ranges)
    # Hard-coded mapping (you can expand)
    expected_ranges = {
        "Acute Gastroenteritis": (3000, 15000),
        "Hypertension": (2000, 8000),
        "Type 2 Diabetes": (5000, 20000),
        "Migraine": (2000, 10000),
        "Asthma": (3000, 15000),
        "Urinary Tract Infection": (2000, 12000),
        "Pneumonia": (15000, 50000),
        "Dengue Fever": (10000, 40000),
        "Typhoid": (8000, 30000),
        "COVID-19": (20000, 100000)
    }
    diagnosis_str = diagnosis.group(1) if diagnosis else ""
    low, high = expected_ranges.get(diagnosis_str, (5000, 50000))
    features['amount_deviation'] = (amount_val - low) / (high - low + 1)  # normalized deviation
    
    # 6. Treatment-diagnosis match? (use a simplified keyword check)
    treatment_str = treatment.group(1).lower() if treatment else ""
    diagnosis_lower = diagnosis_str.lower()
    # Very basic: if "metformin" in treatment and "diabetes" in diagnosis -> match
    match_keywords = {
        "gastroenteritis": ["iv fluids", "antibiotics", "rehydration"],
        "hypertension": ["lisinopril", "amlodipine", "losartan"],
        "diabetes": ["metformin", "insulin"],
        "migraine": ["sumatriptan", "paracetamol"],
        "asthma": ["inhaler", "bronchodilator", "salbutamol"],
        "uti": ["antibiotics", "ciprofloxacin", "nitrofurantoin"],
        "pneumonia": ["azithromycin", "antibiotics", "oxygen"],
        "dengue": ["paracetamol", "iv fluids"],
        "typhoid": ["azithromycin", "ceftriaxone"],
        "covid": ["oseltamivir", "remdesivir"]
    }
    match = 0
    for key, terms in match_keywords.items():
        if key in diagnosis_lower:
            if any(term in treatment_str for term in terms):
                match = 1
            break
    features['treatment_match'] = match
    
    return features