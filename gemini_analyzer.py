import os
import re
import json
from google import genai
from dotenv import load_dotenv
import PIL.Image

# Load API key from .env
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found. Check .env file.")

client = genai.Client(api_key=API_KEY)

def analyze_document(file_path: str):
    """
    Analyzes a medical document (image or text) for forgery.
    Returns a structured dictionary with verdict, flags, explanation, etc.
    """
    # Determine file type
    if file_path.lower().endswith('.txt'):
        with open(file_path, 'r') as f:
            doc_content = f.read()
        contents = [doc_content]
    else:
        # Assume image
        img = PIL.Image.open(file_path)
        contents = [img]

    prompt = """
    You are a medical document forensics expert. Analyze this document for potential forgery.

    Step 1: Extract the following fields (use null if missing):
    - patient_name
    - patient_id
    - admission_date
    - discharge_date
    - diagnosis
    - treatment
    - total_amount
    - insurance_claim_id

    Step 2: Check for logical inconsistencies:
    - Discharge date before admission date
    - Mismatched patient name or ID
    - Unusual medical terms or spelling errors
    - Treatment not matching diagnosis
    - Inflated or unrealistic amounts

    Step 3: Return ONLY valid JSON with this exact structure:
    {
        "extracted_data": { ... },
        "suspicious_flags": ["flag1", "flag2"],
        "forensic_verdict": "suspicious" or "clean",
        "explanation": "short one-sentence explanation",
        "confidence_score": 0.95
    }
    """

    response = client.models.generate_content(
        model="gemini-2.0-flash-exp",
        contents=[prompt] + contents
    )

    # Parse JSON from response
    json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    return {
        "extracted_data": {},
        "suspicious_flags": ["Failed to parse Gemini response"],
        "forensic_verdict": "error",
        "explanation": response.text[:200],
        "confidence_score": 0.0
    }