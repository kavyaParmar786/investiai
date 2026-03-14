"""
groq_ai.py
----------
Free AI engine using Groq API.
- Free tier: 14,400 requests/day, no credit card needed
- Sign up free at https://console.groq.com
- Models: llama3-8b, llama3-70b, mixtral-8x7b, gemma2-9b

Falls back to smart regex/template mode if no key configured.
"""

from __future__ import annotations
import json, os, re

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

try:
    import streamlit as st
    def _get_key():
        # Try Streamlit secrets first (for cloud deploy), then env var
        try:
            return st.secrets.get("GROQ_API_KEY", "") or os.environ.get("GROQ_API_KEY", "")
        except Exception:
            return os.environ.get("GROQ_API_KEY", "")
except ImportError:
    def _get_key():
        return os.environ.get("GROQ_API_KEY", "")

# Best free Groq models in order of preference
GROQ_MODELS = [
    "llama-3.1-8b-instant",   # fastest, great for extraction
    "llama3-8b-8192",
    "gemma2-9b-it",
    "mixtral-8x7b-32768",
    "llama3-70b-8192",        # most powerful but slower
]


def get_client():
    key = _get_key()
    if not key or not GROQ_AVAILABLE:
        return None
    try:
        return Groq(api_key=key)
    except Exception:
        return None


def is_available() -> bool:
    return get_client() is not None


def complete(prompt: str, system: str = "", temperature: float = 0.1,
             max_tokens: int = 1200) -> str:
    """Single call to Groq. Returns response string."""
    client = get_client()
    if not client:
        raise RuntimeError("Groq not available")

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    for model in GROQ_MODELS:
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            err = str(e).lower()
            if "model" in err or "not found" in err:
                continue  # try next model
            raise
    raise RuntimeError("All Groq models failed")


def complete_json(prompt: str, system: str = "", retries: int = 2) -> dict:
    """Call Groq and parse JSON response."""
    for _ in range(retries + 1):
        try:
            raw   = complete(prompt, system=system, temperature=0.05, max_tokens=1500)
            clean = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
            match = re.search(r"\{.*\}", clean, re.DOTALL)
            if match:
                return json.loads(match.group())
            return json.loads(clean)
        except Exception:
            pass
    return {}


def chat(messages: list[dict], system: str = "", temperature: float = 0.5,
         max_tokens: int = 1000) -> str:
    """Multi-turn chat with Groq."""
    client = get_client()
    if not client:
        raise RuntimeError("Groq not available")

    payload = []
    if system:
        payload.append({"role": "system", "content": system})
    for m in messages[-16:]:
        if m.get("role") in ("user", "assistant") and m.get("content"):
            payload.append({"role": m["role"], "content": m["content"]})

    for model in GROQ_MODELS:
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=payload,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            if "model" in str(e).lower():
                continue
            raise
    raise RuntimeError("All Groq models failed")


# ── Task-specific prompts ─────────────────────────────────────────────────────

EXTRACTION_SYSTEM = """You are an expert insurance investigation analyst.
Extract structured information from the document and return ONLY valid JSON:
{"claimant_name":"","age":"","address":"","phone":"","policy_number":"",
"hospital_name":"","hospital_address":"","claim_amount":"","incident_date":"",
"admission_date":"","discharge_date":"","diagnosis":"","doctor_name":"",
"investigator_notes":"","suspicious_indicators":"","treatment_duration":"",
"insurance_company":"","nominee_name":"","relationship":""}
Rules: extract only explicit info, dates as DD Month YYYY, include ₹ in amounts.
Return ONLY the JSON object."""

FRAUD_SYSTEM = """You are an expert insurance fraud investigator.
Return ONLY valid JSON:
{"score":<0-100>,"risk_level":"<Low Risk|Medium Risk|High Risk>",
"explanation":"<2-3 sentences>","indicators":["..."],"recommendations":["..."]}
0-30=Low, 31-65=Medium, 66-100=High. Return ONLY JSON."""

REPORT_SYSTEM = """You are a professional insurance investigation report writer.
Write a formal 3-4 paragraph report in third person with all case facts.
After the report write 'KEY INVESTIGATION POINTS:' with 5-7 bullet points."""

TIMELINE_SYSTEM = """Extract a chronological timeline from case data.
Return ONLY a JSON array:
[{"date":"DD Month YYYY","event":"description","category":"incident|medical|claim|investigation|other"}]
Return ONLY the JSON array."""

AGENT_SYSTEM = """You are InvestiAI Assistant — a helpful AI for insurance investigators.
You know every feature of InvestiAI, insurance investigation techniques,
fraud detection patterns, and Indian insurance regulations (IRDAI).
When given case context, give specific actionable answers.
Be concise and professional."""


def extract_fields(text: str) -> dict:
    result = complete_json(
        f"Extract insurance info from:\n\n{text[:4000]}",
        system=EXTRACTION_SYSTEM)
    return result or {}


def assess_fraud(case_data: dict, form_data: dict) -> dict:
    result = complete_json(
        f"Analyze fraud risk:\n\nCASE: {json.dumps(case_data)[:600]}\n\nFORM: {json.dumps(form_data)[:1200]}\n\nSuspicious: {form_data.get('suspicious_indicators','None')}",
        system=FRAUD_SYSTEM)
    if result and "score" in result:
        s = int(result.get("score", 30))
        result["risk_level"] = "Low Risk" if s <= 30 else ("Medium Risk" if s <= 65 else "High Risk")
    return result or {}


def generate_report(form_data: dict, fraud_data: dict, timeline: list) -> dict:
    raw = complete(
        f"Write investigation report:\n\nCASE: {json.dumps(form_data)[:1500]}\n\nFRAUD: {fraud_data.get('score','?')}/100 — {fraud_data.get('risk_level','?')}\n{fraud_data.get('explanation','')}\n\nTIMELINE: {json.dumps(timeline)[:500]}",
        system=REPORT_SYSTEM, temperature=0.4, max_tokens=1400)

    if "KEY INVESTIGATION POINTS:" in raw:
        parts  = raw.split("KEY INVESTIGATION POINTS:", 1)
        report = parts[0].strip()
        kps    = [l.lstrip("-•* ").strip() for l in parts[1].splitlines() if l.strip().lstrip("-•* ")]
    else:
        report = raw.strip()
        kps    = ["Review completed — see report above"]
    return {"report_text": report, "key_points": kps}


def generate_timeline(form_data: dict, doc_text: str = "") -> list:
    raw = complete(
        f"Extract timeline:\n\nFORM: {json.dumps(form_data)[:1000]}\n\nDOC: {doc_text[:600]}",
        system=TIMELINE_SYSTEM, temperature=0.1, max_tokens=800)
    try:
        clean = re.sub(r"```(?:json)?", "", raw).strip().strip("`")
        match = re.search(r"\[.*\]", clean, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return []


def agent_chat_groq(message: str, history: list[dict], case_context: str = "") -> str:
    system = AGENT_SYSTEM
    if case_context:
        system += f"\n\nCURRENT CASE:\n{case_context}"
    return chat(history + [{"role": "user", "content": message}],
                system=system, temperature=0.5, max_tokens=900)
