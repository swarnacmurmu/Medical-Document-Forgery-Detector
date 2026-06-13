import os
import json
import re
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file")

# Use a confirmed, working model name
MODEL_NAME = "gemini-2.5-flash"  # Replace with a model from your list if needed

client = genai.Client(api_key=GEMINI_API_KEY)

def analyze_document(file_content: str, file_name: str):
    if len(file_content) > 10000:
        file_content = file_content[:10000] + "\n...[truncated]"
    
    prompt = f"""
You are a medical document forensics expert. Analyze the following medical record for signs of forgery.

Medical Record:
{file_content}

Check for:
- Inflated monetary amounts
- Date inconsistency (discharge before admission)
- Treatment not matching diagnosis
- Unusual medical terminology or spelling errors
- Missing critical fields

Return ONLY a JSON object with these keys:
{{
    "forensic_verdict": "clean" or "suspicious",
    "confidence_score": 0.95,
    "suspicious_flags": ["flag1", "flag2"],
    "explanation": "short reason for the verdict"
}}
"""
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[prompt]
        )
        response_text = response.text
        print(f"Gemini Response: {response_text}")  # Debug print
        
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = json.loads(response_text)
        
        # Ensure all keys exist
        default = {
            "forensic_verdict": "error",
            "confidence_score": 0.0,
            "suspicious_flags": [],
            "explanation": "Failed to parse Gemini response."
        }
        for key in default:
            if key not in result:
                result[key] = default[key]
        return result
        
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return {
            "forensic_verdict": "error",
            "confidence_score": 0.0,
            "suspicious_flags": ["analysis_exception"],
            "explanation": f"API Error: {str(e)[:100]}"
        }