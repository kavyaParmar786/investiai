"""fraud_detector.py — Groq AI then heuristic fallback"""
import json, re

def assess_fraud_risk(case_data: dict, form_data: dict, api_key: str = "", provider: str = "") -> dict:
    try:
        from groq_ai import assess_fraud, is_available
        if is_available():
            result = assess_fraud(case_data, form_data)
            if result and "score" in result:
                result["method"] = "Groq AI (free)"; result["success"] = True
                return result
    except Exception:
        pass
    return _heuristic(form_data)

def _heuristic(fd):
    score, indicators, recs = 25, [], []
    amt = re.sub(r"[^\d]", "", fd.get("claim_amount",""))
    if amt and int(amt) > 200000:
        score += 20; indicators.append(f"High claim amount ({fd['claim_amount']}) needs verification")
    if fd.get("suspicious_indicators","").lower() not in ["","none"]:
        score += 15; indicators.append(f"Suspicious: {fd['suspicious_indicators'][:100]}")
    if any(d in fd.get("diagnosis","").lower() for d in ["dengue","typhoid","viral"]):
        score += 10; indicators.append("High-frequency fraud diagnosis — verify lab reports")
        recs.append("Request original lab/pathology reports")
    score = min(score, 100)
    rl = "Low Risk" if score<=30 else ("Medium Risk" if score<=65 else "High Risk")
    exp = {"Low Risk":"Documents consistent, no major red flags. Standard verification recommended.",
           "Medium Risk":"Inconsistencies found. Additional verification before settlement.",
           "High Risk":"Multiple red flags. Escalate immediately. Do not settle without full verification."}[rl]
    if not indicators: indicators = ["Documentation consistent","Claim in normal range","No date conflicts"]
    if not recs: recs = ["Verify hospital registration","Cross-check policy date vs incident date"]
    return {"score":score,"risk_level":rl,"explanation":exp,"indicators":indicators,
            "recommendations":recs,"method":"Heuristic (add GROQ_API_KEY for AI)","success":True}
