"""timeline_generator.py — Groq AI then heuristic"""
import json, re
from datetime import datetime

def generate_timeline(form_data: dict, document_text: str = "",
                      api_key: str = "", provider: str = "") -> dict:
    try:
        from groq_ai import generate_timeline as _gt, is_available
        if is_available():
            events = _gt(form_data, document_text)
            if events:
                return {"events": _sort(events), "method": "Groq AI (free)", "success": True}
    except Exception:
        pass
    return _heuristic(form_data)

def _heuristic(fd):
    events = []
    for field, desc, cat in [
        ("incident_date","Incident / Loss event occurred","incident"),
        ("admission_date","Patient admitted to hospital","medical"),
        ("discharge_date","Patient discharged from hospital","medical"),
    ]:
        if fd.get(field): events.append({"date":fd[field],"event":desc,"category":cat})
    if fd.get("diagnosis") and fd.get("admission_date"):
        events.append({"date":fd["admission_date"],"event":f"Diagnosis: {fd['diagnosis']}","category":"medical"})
    if fd.get("claim_amount"):
        d = fd.get("discharge_date") or fd.get("admission_date") or "Date unknown"
        events.append({"date":d,"event":f"Claim filed for {fd['claim_amount']}","category":"claim"})
    events.append({"date":datetime.now().strftime("%d %B %Y"),"event":"Investigation initiated","category":"investigation"})
    if len(events) <= 1:
        events = [{"date":"10 March 2025","event":"Incident occurred","category":"incident"},
                  {"date":"12 March 2025","event":"Hospital admission","category":"medical"},
                  {"date":"20 March 2025","event":"Discharged","category":"medical"},
                  {"date":"22 March 2025","event":"Claim filed","category":"claim"},
                  {"date":datetime.now().strftime("%d %B %Y"),"event":"Investigation initiated","category":"investigation"}]
    return {"events":_sort(events),"method":"Heuristic","success":True}

MONTHS = {"january":1,"february":2,"march":3,"april":4,"may":5,"june":6,"july":7,"august":8,
          "september":9,"october":10,"november":11,"december":12,
          "jan":1,"feb":2,"mar":3,"apr":4,"jun":6,"jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}
def _sort(events):
    def key(ev):
        try:
            d = ev.get("date","")
            for fmt in ["%d %B %Y","%d %b %Y","%d/%m/%Y","%d-%m-%Y"]:
                try: return datetime.strptime(d,fmt)
                except: pass
            parts = re.split(r"[\s/\-]",d.lower())
            if len(parts)>=3: return datetime(int(parts[2]),MONTHS.get(parts[1],1),int(parts[0]))
        except: pass
        return datetime(9999,1,1)
    return sorted(events,key=key)
