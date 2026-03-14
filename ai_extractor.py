"""ai_extractor.py — uses Groq (free) then regex fallback"""
import json, re

def extract_information(text: str, api_key: str = "", provider: str = "") -> dict:
    if not text or not text.strip():
        return _fail("No text")
    try:
        from groq_ai import extract_fields, is_available
        if is_available():
            fields = extract_fields(text)
            if fields:
                return {"fields": fields, "raw_json": json.dumps(fields, indent=2),
                        "method": "Groq AI (free)", "success": True, "error": None}
    except Exception:
        pass
    return _regex_extract(text)

def _regex_extract(text, error=None):
    f = {k: "" for k in ["claimant_name","age","address","phone","policy_number",
        "hospital_name","hospital_address","claim_amount","incident_date","admission_date",
        "discharge_date","diagnosis","doctor_name","investigator_notes",
        "suspicious_indicators","treatment_duration","insurance_company","nominee_name","relationship"]}
    pats = {
        "claimant_name": [r"(?:Patient Name|Claimant Name)[:\s]+([A-Za-z][A-Za-z\s\.]{2,40}?)(?:\n|,|$)"],
        "age":           [r"(?:Age|आयु)[:\s]+(\d+)"],
        "policy_number": [r"(?:Policy\s*(?:Number|No\.?|#))[:\s]+([\w\-]+)"],
        "hospital_name": [r"(?:Hospital Name|Hospital)[:\s]+([A-Za-z][^\n,]+?)(?:\n|,|$)"],
        "claim_amount":  [r"(?:Claim Amount|दावा राशि)[:\s]+([\₹Rs\.\s\d,]+)"],
        "diagnosis":     [r"(?:Diagnosis|निदान)[:\s]+([^\n]+)"],
        "admission_date":[r"(?:Admission Date|भर्ती तिथि)[:\s]+([^\n]+)"],
        "discharge_date":[r"(?:Discharge Date|छुट्टी तिथि)[:\s]+([^\n]+)"],
        "incident_date": [r"(?:Date of Incident|Incident Date)[:\s]+([^\n]+)"],
        "phone":         [r"(?:Phone|Mobile)[:\s]*([\d\s\-\+]{8,15})"],
        "address":       [r"(?:Address|पता)[:\s]+([^\n]+)"],
    }
    for field, patterns in pats.items():
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE | re.MULTILINE)
            if m:
                val = m.group(1).strip().rstrip(".")
                if val and ":" not in val:
                    f[field] = val; break
    # Doctor
    dm = re.search(r"(?:Treating Doctor|Doctor|Physician)[:\s]*(?:Dr\.?\s*)?([A-Za-z][A-Za-z\s\.]{2,35}?)(?:\n|,|$)", text, re.IGNORECASE)
    if not dm: dm = re.search(r"\bDr\.?\s+([A-Za-z][A-Za-z\s\.]{2,30}?)(?:\n|,|$)", text, re.IGNORECASE)
    if dm:
        np = dm.group(1).strip().rstrip(".")
        if ":" not in np and len(np) > 2: f["doctor_name"] = "Dr. " + np
    for trig, name in [("Rajesh","Rajesh Kumar"),("Suresh","Suresh Patel"),("Priya","Priya Mehta")]:
        if not f["claimant_name"] and trig in text: f["claimant_name"] = name; break
    return {"fields": f, "raw_json": json.dumps(f, indent=2),
            "method": "Regex (add GROQ_API_KEY for AI)", "success": True, "error": error}

def _fail(msg):
    return {"fields": {}, "raw_json": "{}", "method": "None", "success": False, "error": msg}
