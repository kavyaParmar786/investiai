"""report_generator.py — Groq AI then template fallback"""
import json, re
from datetime import datetime
from pathlib import Path

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Table, TableStyle, HRFlowable)
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
    RL = True
except ImportError:
    RL = False

def generate_report(form_data: dict, fraud_data: dict = None,
                    timeline: list = None, api_key: str = "", provider: str = "") -> dict:
    fraud_data = fraud_data or {}; timeline = timeline or []
    try:
        from groq_ai import generate_report as _gr, is_available
        if is_available():
            result = _gr(form_data, fraud_data, timeline)
            if result and result.get("report_text"):
                result["method"] = "Groq AI (free)"; result["success"] = True
                return result
    except Exception:
        pass
    return _template(form_data, fraud_data, timeline)

def _template(fd, fraud, tl):
    n   = fd.get("claimant_name","the claimant") or "the claimant"
    age = fd.get("age",""); hosp = fd.get("hospital_name","the hospital")
    diag = fd.get("diagnosis","the stated condition"); adm = fd.get("admission_date","")
    dis  = fd.get("discharge_date",""); claim = fd.get("claim_amount","")
    doc  = fd.get("doctor_name",""); pol = fd.get("policy_number","")
    susp = fd.get("suspicious_indicators",""); notes = fd.get("investigator_notes","")
    report = f"""INSURANCE INVESTIGATION REPORT
{'='*50}
Date: {datetime.now().strftime('%d %B %Y')}
{'='*50}

This investigation was initiated upon receipt of a claim by {n}{', aged '+age+',' if age else ''} (Policy: {pol or 'on file'}). Submitted documents cover hospitalization at {hosp}.

{n} was admitted to {hosp} on {adm or 'stated date'}{' and discharged on '+dis if dis else ''}{' under '+doc if doc else ''}. Diagnosis: {diag}. Claim: {claim}.

{"Concerns noted: " + susp if susp else "Documentation appears consistent with stated circumstances."} {"Notes: " + notes if notes else ""}

{f"Fraud risk: {fraud.get('score','?')}/100 — {fraud.get('risk_level','?')}. {fraud.get('explanation','')}" if fraud else "Risk assessment pending."}"""
    kps = [f"Claimant: {n}{', '+age if age else ''}",f"Diagnosis: {diag}",
           f"Hospital: {hosp}",f"Claim: {claim}",f"Admission: {adm}",
           f"Risk: {fraud.get('risk_level','Pending') if fraud else 'Pending'}",
           "All documents require independent verification"]
    return {"report_text":report,"key_points":[k for k in kps if k],
            "method":"Template (add GROQ_API_KEY for AI)","success":True,"error":None}

def export_pdf(case_data,form_data,report_text,key_points,fraud_data,timeline,output_path):
    if not RL: return _txt(case_data,report_text,key_points,output_path)
    try:
        doc = SimpleDocTemplate(output_path,pagesize=A4,rightMargin=2*cm,leftMargin=2*cm,topMargin=2*cm,bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        ts = ParagraphStyle("T",parent=styles["Title"],fontSize=18,textColor=colors.HexColor("#1a1a2e"))
        hs = ParagraphStyle("H",parent=styles["Heading2"],fontSize=12,textColor=colors.HexColor("#16213e"),spaceBefore=12)
        bs = ParagraphStyle("B",parent=styles["Normal"],fontSize=10,leading=14,alignment=TA_JUSTIFY)
        story = [Paragraph("InvestiAI",ts),Paragraph("Insurance Investigation Report",styles["Heading2"]),
                 HRFlowable(width="100%",thickness=2,color=colors.HexColor("#0f3460")),Spacer(1,0.3*18)]
        story.append(Paragraph("CASE INFORMATION",hs))
        t=Table([["Case:",case_data.get("case_id","?"),"Status:",case_data.get("status","?")],
                 ["Claimant:",form_data.get("claimant_name","?"),"Policy:",form_data.get("policy_number","?")],
                 ["Hospital:",form_data.get("hospital_name","?"),"Diagnosis:",form_data.get("diagnosis","?")],
                 ["Claim:",form_data.get("claim_amount","?"),"Date:",datetime.now().strftime("%d %B %Y")]],
                colWidths=[2.5*cm,7*cm,2.5*cm,7*cm])
        t.setStyle(TableStyle([("BACKGROUND",(0,0),(0,-1),colors.HexColor("#e8f4fd")),
            ("BACKGROUND",(2,0),(2,-1),colors.HexColor("#e8f4fd")),
            ("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),("FONTNAME",(2,0),(2,-1),"Helvetica-Bold"),
            ("FONTSIZE",(0,0),(-1,-1),9),("GRID",(0,0),(-1,-1),0.5,colors.grey),("PADDING",(0,0),(-1,-1),6)]))
        story.append(t); story.append(Spacer(1,0.2*18))
        if fraud_data:
            score=fraud_data.get("score",0); rl=fraud_data.get("risk_level","?")
            rc=colors.green if score<=30 else (colors.orange if score<=65 else colors.red)
            story.append(Paragraph("FRAUD RISK ASSESSMENT",hs))
            rt=Table([[f"Score: {score}/100",f"Level: {rl}"]],colWidths=[9*cm,9*cm])
            rt.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#fff3f3") if score>65 else colors.HexColor("#f0fff0")),
                ("FONTNAME",(0,0),(-1,-1),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),11),
                ("ALIGN",(0,0),(-1,-1),"CENTER"),("GRID",(0,0),(-1,-1),1,rc),("PADDING",(0,0),(-1,-1),8)]))
            story.append(rt)
            if fraud_data.get("explanation"): story.append(Paragraph(fraud_data["explanation"],bs))
        if timeline:
            story.append(Paragraph("TIMELINE",hs))
            td=[["Date","Event","Category"]]+[[e.get("date",""),e.get("event",""),e.get("category","").title()] for e in timeline]
            tt=Table(td,colWidths=[4*cm,11*cm,3*cm])
            tt.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#0f3460")),
                ("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
                ("FONTSIZE",(0,0),(-1,-1),9),("GRID",(0,0),(-1,-1),0.5,colors.grey),
                ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f5f5f5")]),("PADDING",(0,0),(-1,-1),5)]))
            story.append(tt); story.append(Spacer(1,0.2*18))
        story.append(Paragraph("INVESTIGATION REPORT",hs))
        for p in report_text.split("\n\n"):
            if p.strip(): story.append(Paragraph(p.strip(),bs)); story.append(Spacer(1,0.1*18))
        if key_points:
            story.append(Paragraph("KEY POINTS",hs))
            for p in key_points: story.append(Paragraph(f"✓  {p}",bs))
        story.append(Spacer(1,0.3*18)); story.append(HRFlowable(width="100%",thickness=1,color=colors.grey))
        story.append(Paragraph(f"InvestiAI | {datetime.now().strftime('%d %B %Y %H:%M')} | CONFIDENTIAL",
            ParagraphStyle("F",parent=styles["Normal"],fontSize=8,textColor=colors.grey,alignment=TA_CENTER)))
        doc.build(story); return True
    except Exception: return _txt(case_data,report_text,key_points,output_path)

def _txt(case_data,report_text,key_points,output_path):
    try:
        with open(output_path,"w",encoding="utf-8") as f:
            f.write(f"InvestiAI — {case_data.get('case_id','?')}\n\n{report_text}\n\nKEY POINTS:\n")
            for p in key_points: f.write(f"• {p}\n")
        return True
    except: return False

def export_json(case_data,form_data,report_text,key_points,fraud_data,timeline,output_path):
    try:
        with open(output_path,"w",encoding="utf-8") as f:
            json.dump({"export_date":datetime.now().isoformat(),"generated_by":"InvestiAI",
                "case":case_data,"form_data":form_data,"fraud_assessment":fraud_data,
                "timeline":timeline,"report":report_text,"key_points":key_points},f,indent=2,ensure_ascii=False)
        return True
    except: return False
