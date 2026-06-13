import os
import random
import uuid
from datetime import datetime, timedelta

# === Configuration ===
NUM_FILES = 500   # number of genuine + forged = 1000 total

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
GENUINE_DIR = os.path.join(DATA_DIR, "genuine")
FORGED_DIR = os.path.join(DATA_DIR, "forged")

os.makedirs(GENUINE_DIR, exist_ok=True)
os.makedirs(FORGED_DIR, exist_ok=True)

# === Data pools ===
first_names = ["Rajesh", "Priya", "Amit", "Sunita", "Vikram", "Neha", "Manish", "Anjali", "Rahul", "Pooja"]
last_names = ["Kumar", "Sharma", "Patel", "Verma", "Singh", "Gupta", "Reddy", "Joshi", "Nair", "Menon"]
diagnoses = ["Acute Gastroenteritis", "Hypertension", "Type 2 Diabetes", "Migraine", "Asthma", 
             "Urinary Tract Infection", "Pneumonia", "Dengue Fever", "Typhoid", "COVID-19"]
treatments = ["IV fluids and oral rehydration", "Lisinopril 10mg daily", "Metformin 500mg twice daily",
              "Sumatriptan as needed", "Inhaler and monitoring", "Antibiotics for 5 days",
              "Chest physiotherapy and oxygen", "Rest and paracetamol", "Azithromycin course",
              "Oseltamivir and supportive care"]
hospitals = ["Apollo Hospital", "Fortis Healthcare", "AIIMS", "Manipal Hospital", "Lilavati Hospital"]

# === Diagnosis -> Appropriate Treatments mapping ===
consistent_pairs = {
    "Acute Gastroenteritis": ["IV fluids and oral rehydration", "Antibiotics for 5 days", "Oral rehydration and probiotics"],
    "Hypertension": ["Lisinopril 10mg daily", "Amlodipine 5mg daily", "Losartan 50mg daily"],
    "Type 2 Diabetes": ["Metformin 500mg twice daily", "Insulin as needed", "Metformin and diet counselling"],
    "Migraine": ["Sumatriptan as needed", "Paracetamol and rest", "NSAIDs and dark room"],
    "Asthma": ["Inhaler and monitoring", "Bronchodilators and steroids", "Salbutamol as needed"],
    "Urinary Tract Infection": ["Antibiotics for 5 days", "Ciprofloxacin course", "Nitrofurantoin for 7 days"],
    "Pneumonia": ["Chest physiotherapy and oxygen", "Azithromycin course", "Antibiotics and hydration"],
    "Dengue Fever": ["Rest and paracetamol", "IV fluids and monitoring", "Supportive care"],
    "Typhoid": ["Azithromycin course", "Ceftriaxone IV", "Antibiotics and hydration"],
    "COVID-19": ["Oseltamivir and supportive care", "Remdesivir and oxygen", "Monoclonal antibodies"]
}

def random_date():
    start = datetime.now() - timedelta(days=120)
    return start + timedelta(days=random.randint(0, 120))

def random_amount():
    return random.randint(5000, 200000)

def generate_genuine_record():
    admit = random_date()
    discharge = admit + timedelta(days=random.randint(1, 10))
    diagnosis = random.choice(diagnoses)
    # Choose a treatment that is appropriate for this diagnosis
    possible_treatments = consistent_pairs.get(diagnosis, treatments)  # fallback
    treatment = random.choice(possible_treatments)
    return {
        "Patient Name": f"{random.choice(first_names)} {random.choice(last_names)}",
        "Patient ID": f"P{random.randint(10000, 99999)}",
        "Admission Date": admit.strftime("%Y-%m-%d"),
        "Discharge Date": discharge.strftime("%Y-%m-%d"),
        "Diagnosis": diagnosis,
        "Treatment": treatment,
        "Total Amount": f"₹{random_amount():,}",
        "Insurance Claim ID": str(uuid.uuid4())[:8].upper(),
        "Hospital": random.choice(hospitals)
    }

def generate_forged_from_genuine(genuine):
    forged = genuine.copy()
    modifications = []
    
    # 1. Inflate amount
    if random.choice([True, False]):
        amount_str = genuine["Total Amount"]
        amount = int(amount_str[1:].replace(',', ''))
        forged["Total Amount"] = f"₹{amount * random.randint(2, 20):,}"
        modifications.append("inflated_amount")

    # 2. Date inconsistency (discharge before admission)
    if random.choice([True, False]):
        admit = datetime.strptime(genuine["Admission Date"], "%Y-%m-%d")
        forged["Discharge Date"] = (admit - timedelta(days=random.randint(1, 3))).strftime("%Y-%m-%d")
        modifications.append("date_inconsistency")

    # 3. Force treatment mismatch (use a treatment NOT appropriate for this diagnosis)
    if random.choice([True, False]):
        diagnosis = forged["Diagnosis"]
        appropriate = consistent_pairs.get(diagnosis, [])
        # All treatments from the global list minus the appropriate ones
        wrong_treatments = [t for t in treatments if t not in appropriate]
        if wrong_treatments:
            forged["Treatment"] = random.choice(wrong_treatments)
            modifications.append("treatment_mismatch")

    # 4. Ghost patient (name mismatch)
    if random.choice([True, False]):
        forged["Patient Name"] = f"{random.choice(first_names)} {random.choice(last_names)}"
        modifications.append("patient_name_mismatch")

    # 5. Patient ID mismatch
    if random.choice([True, False]):
        forged["Patient ID"] = f"P{random.randint(10000, 99999)}"
        modifications.append("patient_id_mismatch")

    return forged, modifications

def format_as_text(record):
    return "\n".join([f"{k}: {v}" for k, v in record.items()])

# === Main generation ===
print(f"Generating {NUM_FILES} genuine and {NUM_FILES} forged documents...")
for i in range(NUM_FILES):
    genuine = generate_genuine_record()
    genuine_content = format_as_text(genuine)
    with open(os.path.join(GENUINE_DIR, f"genuine_{i+1}.txt"), "w", encoding='utf-8') as f:
        f.write(genuine_content)
    
    forged, flags = generate_forged_from_genuine(genuine)
    forged_content = format_as_text(forged)
    with open(os.path.join(FORGED_DIR, f"forged_{i+1}.txt"), "w", encoding='utf-8') as f:
        f.write(forged_content)

print("✅ Dataset generation complete!")
print(f"Genuine documents saved to: {GENUINE_DIR}")
print(f"Forged documents saved to: {FORGED_DIR}")