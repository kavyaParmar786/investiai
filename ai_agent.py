"""
ai_agent.py — InvestiAI Cloud Agent
Uses Groq (free) for AI conversations + same action engine.
"""
from __future__ import annotations
import json, os, re

def build_case_context(case_id: str) -> str:
    try:
        from database import (get_case, get_documents, get_extracted_texts,
                              get_translations, get_form_data,
                              get_latest_fraud_score, get_latest_report)
        case=get_case(case_id) or {}; docs=get_documents(case_id)
        exts=get_extracted_texts(case_id); trans=get_translations(case_id)
        form=get_form_data(case_id) or {}; fraud=get_latest_fraud_score(case_id) or {}
        rep=get_latest_report(case_id) or {}
        lines=[f"═══ OPEN CASE: {case_id} ═══",
               f"Claimant : {case.get('claimant_name','?')}",
               f"Policy # : {case.get('policy_number','?')}",
               f"Status   : {case.get('status','?')}",
               f"Docs     : {len(docs)} ({', '.join(d['filename'] for d in docs) or 'none'})",
               f"OCR      : {'Done — '+str(len(exts))+' doc(s)' if exts else 'Not yet'}",
               f"Translated: {'Done — '+str(len(trans))+' doc(s)' if trans else 'Not yet'}"]
        if form:
            for k in ["claimant_name","age","diagnosis","hospital_name","claim_amount",
                      "admission_date","discharge_date","doctor_name","policy_number",
                      "suspicious_indicators","investigator_notes"]:
                v=form.get(k)
                if v: lines.append(f"  {k}: {v}")
        if fraud: lines.append(f"Fraud: {fraud.get('score')}/100 — {fraud.get('risk_level')}")
        lines.append(f"Report: {'Generated' if rep.get('report_text') else 'Not yet'}")
        return "\n".join(lines)
    except Exception as e:
        return f"Case {case_id} (error: {e})"

# ── Tool actions ──────────────────────────────────────────────────────────────
def _t_summary(cid): return build_case_context(cid)

def _t_get_ocr(cid):
    from database import get_extracted_texts
    rows = get_extracted_texts(cid)
    if not rows: return "No OCR text yet. Run OCR in the 🔤 tab first."
    return "\n\n".join(f"[{r.get('filename','?')} | {r.get('detected_lang','?')}]\n{r.get('raw_text','')[:1500]}" for r in rows)

def _t_get_trans(cid):
    from database import get_translations
    rows = get_translations(cid)
    if not rows: return "No translations yet. Run translation in the 🌐 tab first."
    return "\n\n".join(f"[{r.get('filename','?')} | {r.get('source_lang','?')} → English]\n{r.get('translated_text','')[:1500]}" for r in rows)

def _t_retranslate(cid):
    from database import get_extracted_texts, save_translation
    from translator import translate_to_english
    rows = get_extracted_texts(cid)
    if not rows: return "No extracted text — run OCR first."
    non_en = [r for r in rows if r.get("detected_lang") not in ("English","Unknown","")]
    if not non_en: return "All documents already in English."
    out = []
    for r in non_en:
        lang = r.get("detected_lang","Hindi")
        res  = translate_to_english(r.get("raw_text",""), lang)
        if res.get("translated_text"):
            save_translation(r["id"],cid,r["raw_text"],res["translated_text"],lang)
            out.append(f"✅ {r.get('filename','doc')} retranslated from {lang}.\nPreview: {res['translated_text'][:250]}")
        else:
            out.append(f"❌ Failed: {r.get('filename','doc')} — {res.get('error')}")
    return "\n\n".join(out)

def _t_ocr(cid, lang_hint="Auto"):
    from database import get_documents, save_extracted_text
    from ocr_engine import extract_text_from_file
    from handwriting_ocr import extract_handwriting, is_handwritten
    from pathlib import Path
    docs = get_documents(cid)
    if not docs: return "No documents uploaded yet."
    out = []
    for d in docs:
        fp=d.get("filepath","")
        if not Path(fp).exists(): out.append(f"⚠️ Not found: {d['filename']}"); continue
        hw=is_handwritten(fp)
        res=extract_handwriting(fp) if hw else extract_text_from_file(fp,lang_hint)
        txt=res.get("text","")
        if txt:
            save_extracted_text(d["id"],cid,txt,res.get("detected_lang","?"),hw)
            out.append(f"✅ {d['filename']} — {res.get('detected_lang','?')} {len(txt)} chars")
        else:
            out.append(f"❌ {d['filename']} — {res.get('error','no text')}")
    return "\n".join(out)

def _t_reextract(cid):
    from database import get_translations,get_extracted_texts,save_form_data,update_case
    from ai_extractor import extract_information
    trans=get_translations(cid); exts=get_extracted_texts(cid)
    text=("\n\n".join(t.get("translated_text","") for t in trans)
          if trans else "\n\n".join(e.get("raw_text","") for e in exts))
    if not text.strip(): return "No text available — run OCR and translation first."
    res=extract_information(text)
    if res["success"]:
        fields={k:v for k,v in res["fields"].items() if v}
        fields["raw_json"]=res["raw_json"]; save_form_data(cid,fields)
        if fields.get("claimant_name"): update_case(cid,claimant_name=fields["claimant_name"])
        if fields.get("policy_number"): update_case(cid,policy_number=fields["policy_number"])
        return f"✅ Extracted ({res['method']}):\n"+"\n".join(f"  • {k.replace('_',' ').title()}: {v}" for k,v in fields.items() if k!="raw_json" and v)
    return f"❌ Failed: {res.get('error')}"

def _t_fraud(cid):
    from database import get_case,get_form_data,save_fraud_score
    from fraud_detector import assess_fraud_risk
    res=assess_fraud_risk(get_case(cid) or {},get_form_data(cid) or {})
    save_fraud_score(cid,res["score"],res["risk_level"],res["explanation"],json.dumps(res.get("indicators",[])))
    lines=[f"✅ Fraud ({res['method']})",f"Score: {res['score']}/100 | Level: {res['risk_level']}","",res["explanation"]]
    if res.get("indicators"): lines+=["","Indicators:"]+[f"  • {i}" for i in res["indicators"]]
    if res.get("recommendations"): lines+=["","Recommendations:"]+[f"  → {r}" for r in res["recommendations"]]
    return "\n".join(lines)

def _t_report(cid):
    from database import get_form_data,get_latest_fraud_score,get_latest_report,save_report
    from report_generator import generate_report
    form=get_form_data(cid) or {}; fraud=get_latest_fraud_score(cid) or {}
    saved=get_latest_report(cid) or {}
    tl=[]
    try: tl=json.loads(saved.get("timeline_json","[]"))
    except: pass
    res=generate_report(form,fraud,tl)
    save_report(cid,res["report_text"],json.dumps(res["key_points"]),json.dumps(tl))
    return f"✅ Report regenerated ({res['method']}).\n\nPreview:\n{res['report_text'][:400]}…\n\nKey Points:\n"+"\n".join(f"  ✓ {p}" for p in res["key_points"][:5])

def _t_timeline(cid):
    from database import get_form_data,get_extracted_texts,get_latest_report,save_report
    from timeline_generator import generate_timeline
    form=get_form_data(cid) or {}; exts=get_extracted_texts(cid)
    res=generate_timeline(form," ".join(e.get("raw_text","") for e in exts))
    events=res.get("events",[])
    saved=get_latest_report(cid) or {}
    save_report(cid,saved.get("report_text",""),saved.get("key_points",""),json.dumps(events))
    emojis={"incident":"⚡","medical":"🏥","claim":"📋","investigation":"🔍","other":"📌"}
    return f"✅ Timeline ({res['method']}) — {len(events)} events:\n"+"\n".join(f"  {emojis.get(ev.get('category','other'),'📌')} {ev.get('date','?')} — {ev.get('event','')}" for ev in events)

def _t_update(cid, field_name, new_value):
    VALID={"claimant_name","age","address","phone","policy_number","hospital_name",
           "hospital_address","claim_amount","incident_date","admission_date","discharge_date",
           "diagnosis","doctor_name","investigator_notes","suspicious_indicators",
           "treatment_duration","insurance_company","nominee_name","relationship"}
    from database import save_form_data,update_case
    fn=field_name.lower().replace(" ","_").replace("-","_")
    if fn not in VALID:
        for v in VALID:
            if fn in v or v in fn: fn=v; break
        else: return f"❌ Unknown field '{field_name}'. Valid: {', '.join(sorted(VALID))}"
    save_form_data(cid,{fn:new_value})
    if fn=="claimant_name": update_case(cid,claimant_name=new_value)
    if fn=="policy_number":  update_case(cid,policy_number=new_value)
    return f"✅ Updated **{fn.replace('_',' ').title()}** → {new_value}"

# ── Main entry point ──────────────────────────────────────────────────────────
def ask_agent(message: str, history: list[dict], case_id: str | None, api_key: str = "") -> tuple[str, list[dict]]:
    if not message.strip():
        return "Please type a message!", history
    new_history = history + [{"role":"user","content":message}]
    action = _check_actions(message, case_id)
    if action is not None:
        try:
            from groq_ai import agent_chat_groq, is_available
            if is_available():
                ctx = build_case_context(case_id) if case_id else ""
                summary = agent_chat_groq(
                    f"User asked: '{message}'. Action result:\n\n{action}\n\nConfirm briefly (2 sentences).",
                    [], ctx)
                response = f"**Action done:**\n\n{action}\n\n---\n\n{summary}"
            else:
                response = action
        except Exception:
            response = action
        new_history.append({"role":"assistant","content":response})
        return response, new_history

    # Groq conversation
    try:
        from groq_ai import agent_chat_groq, is_available
        if is_available():
            ctx = build_case_context(case_id) if case_id else ""
            response = agent_chat_groq(message, history[-14:], ctx)
            new_history.append({"role":"assistant","content":response})
            return response, new_history
    except Exception:
        pass

    response = _rule_based(message, case_id)
    new_history.append({"role":"assistant","content":response})
    return response, new_history

def _check_actions(message, case_id):
    if not case_id: return None
    msg = message.lower().strip()
    if any(w in msg for w in ["retranslat","translate again","bad translation","wrong translat","fix translat"]): return _t_retranslate(case_id)
    if any(w in msg for w in ["rerun ocr","run ocr again","redo ocr","re-ocr","extract text again"]): return _t_ocr(case_id)
    if any(w in msg for w in ["reextract","re-extract","extract again","fill form again","refill"]): return _t_reextract(case_id)
    if any(w in msg for w in ["fraud again","rerun fraud","check fraud","reassess fraud","risk again"]): return _t_fraud(case_id)
    if any(w in msg for w in ["regenerate report","redo report","new report","rewrite report"]): return _t_report(case_id)
    if any(w in msg for w in ["regenerate timeline","redo timeline","update timeline","rebuild timeline"]): return _t_timeline(case_id)
    if any(w in msg for w in ["summary","what have we done","case status","case info","show case","everything done"]): return _t_summary(case_id)
    if any(w in msg for w in ["extracted text","ocr text","show text","what was extracted"]): return _t_get_ocr(case_id)
    if any(w in msg for w in ["translated text","show translation","translation text"]): return _t_get_trans(case_id)
    FIELD_MAP={"diagnosis":"diagnosis","claimant":"claimant_name","name":"claimant_name","hospital":"hospital_name",
               "doctor":"doctor_name","amount":"claim_amount","claim amount":"claim_amount",
               "admission":"admission_date","discharge":"discharge_date","age":"age","address":"address",
               "phone":"phone","mobile":"phone","policy":"policy_number","notes":"investigator_notes","suspicious":"suspicious_indicators"}
    for keyword,field in FIELD_MAP.items():
        for pat in [rf"(?:change|set|update|correct|fix|edit)\s+(?:the\s+)?{re.escape(keyword)}[^\w]{{0,12}}(?:to|as|:)\s+(.+)",
                    rf"{re.escape(keyword)}\s+(?:should be|is now|is|:)\s+(.+)"]:
            m=re.search(pat,msg,re.IGNORECASE)
            if m:
                val=m.group(1).strip().strip("\"'.,")
                return _t_update(case_id,field,val)
    return None

def _rule_based(message, case_id):
    msg=message.lower().strip()
    if any(w in msg for w in ["hello","hi ","hey ","namaste"]):
        return (f"👋 Hello! I'm InvestiAI Assistant.{' Case **'+case_id+'** is open.' if case_id else ''}\n\n"
                "I can take **actions** on your case and answer **any insurance question**.\n\n"
                "Try: *'show case summary'*, *'change diagnosis to typhoid'*, *'re-run fraud assessment'*")
    KB=[
        (["create case","new case"],"Click **➕ New Case** in sidebar → fill Case ID, Claimant Name, Policy Number → ✅ Create Case."),
        (["upload","documents"],"**📤 Documents** tab → drag & drop JPG/PNG/PDF files."),
        (["ocr","extract text"],"**🔤 OCR** tab → choose language (Auto/Hindi/Gujarati/English) → click Run OCR."),
        (["translat"],"**🌐 Translation** tab → click Translate All. Side-by-side view."),
        (["fraud score","risk score"],"0–30=🟢Low · 31–65=🟡Medium · 66–100=🔴High"),
        (["export","pdf"],"**📤 Export** tab → choose PDF or JSON → download."),
        (["groq","api key","free ai"],"Go to https://console.groq.com → sign up free → create API key → add in ⚙️ Settings."),
        (["fraud pattern"],"Common: altered bills, fabricated diagnoses, policy taken just before claim, duplicate claims."),
        (["escalate"],"Escalate when: score>65, hospital unverifiable, doctor registration invalid, claimant uncooperative."),
        (["waiting period"],"Initial 30 days (accidents excluded) · Pre-existing: 2–4 years · Claims during waiting period = red flag."),
        (["irdai"],"IRDAI regulates Indian insurance. Claims settle in 30 days (45 with investigation). Escalate: bimabharosa.irdai.gov.in."),
        (["thank","great","perfect"],"You're welcome! 😊"),
    ]
    for keywords,answer in KB:
        if any(k in msg for k in keywords): return answer
    return ("I can help! **Actions**: retranslate · re-OCR · update form fields · re-run fraud · regenerate report\n\n"
            "**Questions**: InvestiAI features · fraud patterns · IRDAI · investigation tips\n\n"
            "Just ask!")

_CASE_CHIPS=["Show case summary","Retranslate documents","Re-run fraud assessment","Regenerate report","Re-extract information","Show extracted text"]
_NO_CASE_CHIPS=["How do I upload documents?","What are common fraud patterns?","When should I escalate?","How do I get a free Groq API key?"]

def get_quick_questions(case_id=None, n=4):
    import random
    pool=_CASE_CHIPS if case_id else _NO_CASE_CHIPS
    return random.sample(pool,min(n,len(pool)))
