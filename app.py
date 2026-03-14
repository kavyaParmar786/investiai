"""
app.py — InvestiAI Cloud
Public web app with email/password + Google + GitHub login.
Free AI via Groq. Deploys free on Streamlit Community Cloud.
"""

import os, json
from pathlib import Path
from datetime import datetime

import streamlit as st

st.set_page_config(
    page_title="InvestiAI – Investigation Assistant",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Modules ───────────────────────────────────────────────────────────────────
from database import (
    init_db, create_case, get_all_cases, get_case, update_case, delete_case,
    search_cases, get_documents, save_document, get_extracted_texts,
    save_extracted_text, get_translations, save_translation,
    save_form_data, get_form_data, save_report, get_latest_report,
    save_fraud_score, get_latest_fraud_score, get_case_stats,
)
from auth_cloud import require_auth, logout, get_current_user, init_session
from utils import (
    APP_CSS, generate_case_id, save_uploaded_file, format_file_size,
    get_risk_color, get_risk_emoji, get_status_color, get_export_path,
    get_timeline_category_emoji, truncate_text, ensure_dirs,
)
from ocr_engine import extract_text_from_file
from handwriting_ocr import extract_handwriting, is_handwritten
from translator import translate_to_english
from ai_extractor import extract_information
from fraud_detector import assess_fraud_risk
from timeline_generator import generate_timeline
from report_generator import generate_report, export_pdf, export_json
from ai_agent import ask_agent, get_quick_questions

# ── Bootstrap ─────────────────────────────────────────────────────────────────
init_db()
ensure_dirs()
init_session()
require_auth()
st.markdown(APP_CSS, unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
def nav_to(page: str, case_id: str = None):
    st.session_state.page = page
    if case_id:
        st.session_state.current_case_id = case_id
    st.rerun()

def get_api_key() -> str:
    """Groq key from secrets (cloud) or env (local)."""
    try:
        return (st.secrets.get("GROQ_API_KEY","")
                or os.environ.get("GROQ_API_KEY",""))
    except Exception:
        return os.environ.get("GROQ_API_KEY","")

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
def render_sidebar():
    user = get_current_user() or {}
    with st.sidebar:
        st.markdown("""
        <div style="text-align:center;padding:1.5rem 0 1rem">
          <div style="font-size:2rem">🔍</div>
          <div style="font-size:1.4rem;font-weight:800;letter-spacing:-0.5px;margin-top:.3rem">InvestiAI</div>
          <div style="font-size:.72rem;opacity:.7;letter-spacing:.1em;text-transform:uppercase">Investigation Platform</div>
        </div>
        <hr style="border-color:rgba(255,255,255,.15);margin:0 0 1rem">
        """, unsafe_allow_html=True)

        # Avatar + user info
        avatar = user.get("avatar_url","")
        provider_badge = {"google":"🔵 Google","github":"⚫ GitHub","email":"📧 Email"}.get(user.get("provider","email"),"")
        if avatar:
            st.markdown(f"""
            <div style="background:rgba(255,255,255,.1);border-radius:10px;padding:.75rem 1rem;margin-bottom:1.2rem;display:flex;align-items:center;gap:.75rem">
              <img src="{avatar}" style="width:36px;height:36px;border-radius:50%;border:2px solid rgba(255,255,255,.3)">
              <div>
                <div style="font-weight:700;font-size:.95rem">{user.get('full_name','User')}</div>
                <div style="font-size:.72rem;opacity:.65">{provider_badge} · {user.get('role','investigator').title()}</div>
              </div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="background:rgba(255,255,255,.1);border-radius:10px;padding:.75rem 1rem;margin-bottom:1.2rem">
              <div style="font-weight:700;font-size:.95rem">{user.get('full_name','User')}</div>
              <div style="font-size:.72rem;opacity:.65">{provider_badge} · {user.get('role','investigator').title()}</div>
            </div>""", unsafe_allow_html=True)

        for icon, page_key, label in [
            ("📊","dashboard","Dashboard"),
            ("📁","new_case","New Case"),
            ("🤖","help_agent","AI Help Agent"),
            ("⚙️","settings","Settings"),
        ]:
            if st.button(f"{icon}  {label}", key=f"nav_{page_key}", use_container_width=True):
                nav_to(page_key)

        if (st.session_state.current_case_id
                and st.session_state.page not in ("dashboard","new_case","settings","help_agent")):
            st.markdown("<hr style='border-color:rgba(255,255,255,.15);margin:.8rem 0'>",unsafe_allow_html=True)
            cid = st.session_state.current_case_id
            st.markdown(f"<div style='font-size:.7rem;opacity:.65;text-transform:uppercase;letter-spacing:.08em'>Active Case</div>",unsafe_allow_html=True)
            st.markdown(f"<div style='font-weight:700;font-size:.9rem;margin:.2rem 0 .5rem'>{cid}</div>",unsafe_allow_html=True)

        st.markdown("<hr style='border-color:rgba(255,255,255,.15);margin:1rem 0 .75rem'>",unsafe_allow_html=True)
        if st.button("🚪  Sign Out", use_container_width=True):
            logout(); st.rerun()

        st.markdown("""
        <div style="text-align:center;opacity:.4;font-size:.68rem;margin-top:1rem">
        InvestiAI v2.0 · Cloud Edition<br>© 2025 All rights reserved
        </div>""", unsafe_allow_html=True)

# ── DASHBOARD ─────────────────────────────────────────────────────────────────
def page_dashboard():
    user = get_current_user() or {}
    st.markdown(f"<div style='font-size:1.75rem;font-weight:800;color:#0f3460;letter-spacing:-.5px;margin-bottom:1.5rem'>Investigation Dashboard</div>",unsafe_allow_html=True)

    stats = get_case_stats()
    c1,c2,c3,c4 = st.columns(4)
    for col,val,label,color in [(c1,stats["total"],"Total Cases","#0f3460"),
                                 (c2,stats["open"],"Open Cases","#3498db"),
                                 (c3,stats["closed"],"Closed","#27ae60"),
                                 (c4,stats["high_risk"],"High Risk","#e74c3c")]:
        with col:
            st.markdown(f"""<div class="metric-card" style="border-left-color:{color}">
              <div class="metric-value" style="color:{color}">{val}</div>
              <div class="metric-label">{label}</div></div>""",unsafe_allow_html=True)

    st.markdown("<hr style='margin:.5rem 0 1.5rem;border-color:#eef2f7'>",unsafe_allow_html=True)

    cc1,cc2,cc3 = st.columns([2,1,1])
    with cc1: q = st.text_input("","",placeholder="🔍  Search by name, ID, or policy…",label_visibility="collapsed")
    with cc2: sf = st.selectbox("",["All Statuses","Open","In Progress","Closed","Escalated"],label_visibility="collapsed")
    with cc3:
        if st.button("➕  New Case",use_container_width=True,type="primary"): nav_to("new_case")

    cases = search_cases(q) if q else get_all_cases()
    if sf != "All Statuses": cases = [c for c in cases if c["status"]==sf]

    if not cases:
        st.markdown("<div style='text-align:center;padding:3rem;color:#aaa'><div style='font-size:3rem'>📂</div><div style='font-size:1.1rem;font-weight:600;margin-top:1rem'>No cases found</div></div>",unsafe_allow_html=True)
        return

    st.markdown("""<div style="display:grid;grid-template-columns:1.2fr 1.5fr 1.3fr .9fr 1.1fr 1fr;
      padding:.5rem .75rem;background:#f7f9fc;border-radius:8px;margin-bottom:.5rem;
      font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#888">
      <span>Case ID</span><span>Claimant</span><span>Policy</span><span>Status</span><span>Created</span><span>Actions</span>
    </div>""",unsafe_allow_html=True)

    for case in cases:
        sc = get_status_color(case["status"])
        cols = st.columns([1.2,1.5,1.3,.9,1.1,1])
        with cols[0]: st.markdown(f"<div style='font-family:monospace;font-size:.82rem;font-weight:600;color:#0f3460;padding:.6rem 0'>{case['case_id']}</div>",unsafe_allow_html=True)
        with cols[1]: st.markdown(f"<div style='font-size:.88rem;font-weight:600;padding:.6rem 0'>{case.get('claimant_name') or '—'}</div>",unsafe_allow_html=True)
        with cols[2]: st.markdown(f"<div style='font-size:.85rem;color:#555;padding:.6rem 0'>{case.get('policy_number') or '—'}</div>",unsafe_allow_html=True)
        with cols[3]: st.markdown(f"<div style='padding:.6rem 0'><span class='status-badge' style='background:{sc}'>{case['status']}</span></div>",unsafe_allow_html=True)
        with cols[4]: st.markdown(f"<div style='font-size:.82rem;color:#777;padding:.6rem 0'>{(case.get('created_at') or '')[:10] or '—'}</div>",unsafe_allow_html=True)
        with cols[5]:
            bc = st.columns(3)
            with bc[0]:
                if st.button("📂",key=f"o_{case['case_id']}",help="Open"): nav_to("case_workspace",case["case_id"])
            with bc[1]:
                if st.button("✏️",key=f"e_{case['case_id']}",help="Edit"):
                    st.session_state[f"editing_{case['case_id']}"]=True; st.rerun()
            with bc[2]:
                if st.button("🗑️",key=f"d_{case['case_id']}",help="Delete"):
                    st.session_state[f"cdel_{case['case_id']}"]=True; st.rerun()
        if st.session_state.get(f"cdel_{case['case_id']}"):
            st.warning(f"⚠️ Delete **{case['case_id']}**?")
            da,db,_ = st.columns([1,1,4])
            with da:
                if st.button("Delete",key=f"cdy_{case['case_id']}",type="primary"):
                    delete_case(case["case_id"]); del st.session_state[f"cdel_{case['case_id']}"]; st.rerun()
            with db:
                if st.button("Cancel",key=f"cdn_{case['case_id']}"):
                    del st.session_state[f"cdel_{case['case_id']}"]; st.rerun()
        st.markdown("<hr style='margin:.25rem 0;border-color:#f0f4f8'>",unsafe_allow_html=True)

# ── NEW CASE ──────────────────────────────────────────────────────────────────
def page_new_case():
    st.markdown("<div style='font-size:1.75rem;font-weight:800;color:#0f3460;margin-bottom:1.5rem'>Create New Case</div>",unsafe_allow_html=True)
    user = get_current_user() or {}
    col_form,col_help = st.columns([2,1])
    with col_form:
        with st.form("new_case_form"):
            st.markdown("<div class='section-header'>Case Information</div>",unsafe_allow_html=True)
            cid  = st.text_input("Case ID *",value=generate_case_id())
            name = st.text_input("Claimant Name *",placeholder="Full name of claimant")
            pol  = st.text_input("Policy Number",placeholder="e.g. POL-2024-123456")
            ca,cb = st.columns(2)
            with ca: status = st.selectbox("Status",["Open","In Progress","Closed","Escalated"])
            with cb: asgn = st.text_input("Assigned To",value=user.get("full_name",""))
            notes = st.text_area("Initial Notes",height=80)
            if st.form_submit_button("✅  Create Case",use_container_width=True,type="primary"):
                if not cid or not name:
                    st.error("Case ID and Claimant Name are required.")
                else:
                    try:
                        create_case(cid,name,pol,asgn,notes)
                        update_case(cid,status=status)
                        st.success(f"✅ Case {cid} created!")
                        nav_to("case_workspace",cid)
                    except Exception as e:
                        st.error(f"Error: {e}")
    with col_help:
        st.markdown("""<div class="section-card">
          <div class="section-header">Quick Guide</div>
          <p style="font-size:.88rem;color:#555">
          After creating a case:<br><br>
          📤 <b>Upload documents</b> (JPG/PNG/PDF)<br><br>
          🔤 <b>Extract text</b> via OCR<br><br>
          🌐 <b>Translate</b> Hindi/Gujarati<br><br>
          🤖 <b>AI extraction</b> fills the form<br><br>
          🚨 <b>Fraud scoring</b> and reporting
          </p></div>""",unsafe_allow_html=True)

# ── SETTINGS ──────────────────────────────────────────────────────────────────
def page_settings():
    st.markdown("<div style='font-size:1.75rem;font-weight:800;color:#0f3460;margin-bottom:1.5rem'>Settings</div>",unsafe_allow_html=True)
    stab1, stab2 = st.tabs(["⚙️  General & OCR", "🤖  AI Setup (Free — Groq)"])

    with stab2:
        _render_groq_setup()
    with stab1:
        c1,c2 = st.columns([2,1])
        with c1:
            st.markdown("<div class='section-card'>",unsafe_allow_html=True)
            st.markdown("<div class='section-header'>🔑 Groq AI Key</div>",unsafe_allow_html=True)
            st.info("Groq is FREE — sign up at https://console.groq.com and get a free API key. No credit card needed. 14,400 requests/day free.")
            cur = get_api_key()
            masked = ("*"*(len(cur)-4)+cur[-4:]) if len(cur)>8 else cur
            new_key = st.text_input("Groq API Key",value="",type="password",
                                    placeholder=f"Current: {masked or 'Not set — demo mode'}",
                                    help="Store in .streamlit/secrets.toml on server for permanent use.")
            if st.button("Save Key",type="primary"):
                if new_key:
                    os.environ["GROQ_API_KEY"] = new_key
                    st.success("✅ Key saved for this session. Add to secrets.toml for permanent use.")
                else:
                    st.warning("No key entered.")
            st.markdown("</div>",unsafe_allow_html=True)
            st.markdown("<div class='section-card'>",unsafe_allow_html=True)
            st.markdown("<div class='section-header'>⚙️ OCR Settings</div>",unsafe_allow_html=True)
            st.selectbox("Default OCR Language",["Auto-Detect","Hindi","Gujarati","English"],key="ocr_lang")
            st.checkbox("Enable Handwriting Detection",value=True,key="enable_hw_detection")
            st.checkbox("Auto-translate non-English text",value=True,key="auto_translate")
            if st.button("Save OCR Settings",type="primary"): st.success("✅ Saved.")
            st.markdown("</div>",unsafe_allow_html=True)
        with c2:
            st.markdown("<div class='section-card'><div class='section-header'>ℹ️ System Info</div>",unsafe_allow_html=True)
            checks = []
            try: import pytesseract; pytesseract.get_tesseract_version(); checks.append(("✅","Tesseract OCR","Available"))
            except: checks.append(("⚠️","Tesseract OCR","Demo mode"))
            try: import easyocr; checks.append(("✅","EasyOCR","Available"))
            except: checks.append(("⚠️","EasyOCR","Demo mode"))
            try: from googletrans import Translator; checks.append(("✅","Google Translate","Available"))
            except: checks.append(("⚠️","googletrans","Demo mode"))
            try:
                from groq_ai import is_available
                if is_available(): checks.append(("✅","Groq AI","Connected — Free AI active!"))
                else: checks.append(("⚠️","Groq AI","No key — demo mode"))
            except: checks.append(("⚠️","Groq AI","Not installed"))
            try: from reportlab.lib.pagesizes import A4; checks.append(("✅","ReportLab PDF","Available"))
            except: checks.append(("⚠️","ReportLab","Demo mode"))
            for icon,name,status in checks:
                st.markdown(f"<div style='padding:.3rem 0;font-size:.82rem'>{icon} <b>{name}</b><br><span style='color:#888;font-size:.75rem;padding-left:1.5rem'>{status}</span></div>",unsafe_allow_html=True)
            st.markdown("</div>",unsafe_allow_html=True)

def _render_groq_setup():
    """Groq AI setup instructions."""
    try:
        from groq_ai import is_available
        groq_ok = is_available()
    except Exception:
        groq_ok = False

    if groq_ok:
        st.markdown("""
        <div style="background:#e8f5e9;border:1px solid #a5d6a7;border-radius:10px;padding:1rem 1.25rem;margin-bottom:1.5rem;display:flex;align-items:center;gap:1rem">
          <div style="font-size:1.8rem">🟢</div>
          <div><div style="font-weight:700;color:#1b5e20">Groq AI is connected!</div>
          <div style="color:#2e7d32;font-size:.88rem">Free AI features are active. No cost, no limits for normal use.</div></div>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background:#fff3e0;border:1px solid #ffcc02;border-radius:10px;padding:1rem 1.25rem;margin-bottom:1.5rem">
          <div style="font-weight:700;color:#e65100;margin-bottom:.5rem">⚠️ Groq not connected — add your free key</div>
          <div style="color:#bf360c;font-size:.88rem">App works in demo mode without it. AI features use smart templates.</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("### How to get your FREE Groq API key")
    st.markdown("""
    Groq gives you **14,400 free AI requests per day** — more than enough for insurance investigation work. No credit card needed.
    """)

    steps = [
        ("1", "Go to Groq website", "Visit **https://console.groq.com** and click **Sign Up**"),
        ("2", "Create free account", "Sign up with your email or Google account — it's instant"),
        ("3", "Get your API key", "Click **API Keys** in the left menu → **Create API Key** → Copy it"),
        ("4", "Add to InvestiAI", "Paste it in the **Groq API Key** field in the General tab above"),
    ]
    for num, title, desc in steps:
        st.markdown(f"""
        <div style="display:flex;gap:1rem;padding:.75rem 0;border-bottom:1px solid #f0f4f8;align-items:flex-start">
          <div style="background:#0f3460;color:white;border-radius:50%;width:28px;height:28px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:.85rem;flex-shrink:0">{num}</div>
          <div><div style="font-weight:700;font-size:.9rem;color:#1a1a2e">{title}</div>
          <div style="font-size:.84rem;color:#555;margin-top:.15rem">{desc}</div></div>
        </div>""", unsafe_allow_html=True)

    st.markdown("### For permanent setup on your server")
    st.markdown("Add to `.streamlit/secrets.toml` on your server:")
    st.code('[secrets]\nGROQ_API_KEY = "gsk_your_key_here"', language="toml")
    st.markdown("Or set as environment variable:")
    st.code("export GROQ_API_KEY=gsk_your_key_here", language="bash")

    st.markdown("### Free tier limits")
    st.info("Free: 14,400 requests/day · 30 requests/minute · No credit card · Resets daily")

# ── CASE WORKSPACE ────────────────────────────────────────────────────────────
def page_case_workspace():
    cid = st.session_state.current_case_id
    if not cid:
        st.error("No case selected.")
        if st.button("← Dashboard"): nav_to("dashboard")
        return
    case = get_case(cid)
    if not case:
        st.error(f"Case {cid} not found."); nav_to("dashboard"); return

    sc = get_status_color(case["status"])
    st.markdown(f"""<div style="display:flex;align-items:center;gap:1rem;margin-bottom:.5rem;flex-wrap:wrap">
      <div style="font-size:1.6rem;font-weight:800;color:#0f3460;letter-spacing:-.5px">{case.get('claimant_name') or 'Unnamed Claimant'}</div>
      <span class="status-badge" style="background:{sc};font-size:.8rem">{case['status']}</span>
    </div>
    <div style="font-family:monospace;font-size:.85rem;color:#888;margin-bottom:1.5rem">{cid}{' · Policy: '+case['policy_number'] if case.get('policy_number') else ''}</div>
    """,unsafe_allow_html=True)

    qc1,qc2,_ = st.columns([1.5,1,3])
    with qc1:
        ns = st.selectbox("",["Open","In Progress","Closed","Escalated"],
            index=["Open","In Progress","Closed","Escalated"].index(case["status"]),
            key="case_status_sel",label_visibility="collapsed")
        if ns != case["status"]:
            update_case(cid,status=ns); st.rerun()
    with qc2:
        if st.button("← Dashboard",use_container_width=True): nav_to("dashboard")

    tabs = st.tabs(["📤 Documents","🔤 OCR","🌐 Translation","🤖 AI Extraction",
                    "📝 Form","📊 Report","🚨 Fraud","📅 Timeline","📤 Export"])
    with tabs[0]: tab_documents(cid, case)
    with tabs[1]: tab_ocr(cid)
    with tabs[2]: tab_translation(cid)
    with tabs[3]: tab_ai_extraction(cid)
    with tabs[4]: tab_investigation_form(cid, case)
    with tabs[5]: tab_report(cid, case)
    with tabs[6]: tab_fraud_risk(cid, case)
    with tabs[7]: tab_timeline(cid)
    with tabs[8]: tab_export(cid, case)


# ─── TAB: DOCUMENTS ──────────────────────────────────────────────────────────

def tab_documents(case_id, case):
    st.markdown("<div class='section-header'>📤 Document Upload</div>", unsafe_allow_html=True)

    col_upload, col_docs = st.columns([1, 1])

    with col_upload:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown("**Upload New Documents**")
        uploaded_files = st.file_uploader(
            "Choose files",
            type=["jpg", "jpeg", "png", "pdf"],
            accept_multiple_files=True,
            help="Supported: JPG, PNG, PDF. Multiple files allowed.",
            label_visibility="collapsed",
        )

        if uploaded_files:
            for uf in uploaded_files:
                result = save_uploaded_file(uf, case_id)
                if result["success"]:
                    doc_id = save_document(case_id, result["filename"], result["filepath"])
                    st.success(f"✅ Uploaded: {result['filename']} ({format_file_size(result['size'])})")
                else:
                    st.error(f"❌ Failed: {uf.name}")
            st.info("💡 Go to 'OCR & Text' tab to extract text from uploaded documents.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_docs:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown("**Uploaded Documents**")
        docs = get_documents(case_id)

        if not docs:
            st.markdown("<div style='text-align:center; color:#aaa; padding:2rem;'>📄 No documents yet</div>", unsafe_allow_html=True)
        else:
            for doc in docs:
                fpath = Path(doc["filepath"])
                exists = fpath.exists()
                ext = fpath.suffix.lower()
                icon = "🖼️" if ext in [".jpg", ".jpeg", ".png"] else "📄"

                with st.expander(f"{icon} {doc['filename']}", expanded=False):
                    if exists:
                        if ext in [".jpg", ".jpeg", ".png"]:
                            try:
                                st.image(str(fpath), use_column_width=True)
                            except Exception:
                                st.write("Preview unavailable")
                        elif ext == ".pdf":
                            st.write(f"📄 PDF document — {doc['filename']}")
                        st.caption(f"Uploaded: {doc['uploaded_at'][:16] if doc.get('uploaded_at') else 'Unknown'}")
                    else:
                        st.warning("File not found on disk.")
        st.markdown("</div>", unsafe_allow_html=True)


# ─── TAB: OCR ────────────────────────────────────────────────────────────────

def tab_ocr(case_id):
    st.markdown("<div class='section-header'>🔤 OCR Text Extraction</div>", unsafe_allow_html=True)

    docs = get_documents(case_id)
    if not docs:
        st.info("📤 Upload documents first in the Documents tab.")
        return

    col_ctrl, _ = st.columns([2, 1])
    with col_ctrl:
        lang_hint = st.selectbox("OCR Language Hint", ["Auto", "Hindi", "Gujarati", "English"],
                                  index=0, key="ocr_lang_hint")

    if st.button("🔍  Run OCR on All Documents", type="primary"):
        with st.spinner("Extracting text from documents..."):
            for doc in docs:
                fpath = doc["filepath"]
                if not Path(fpath).exists():
                    st.warning(f"File not found: {doc['filename']}")
                    continue

                # Check if handwritten
                hw = False
                if st.session_state.get("enable_hw_detection", True):
                    hw = is_handwritten(fpath)

                if hw:
                    st.info(f"✍️ {doc['filename']} — Handwriting detected, using EasyOCR")
                    result = extract_handwriting(fpath)
                    method = result.get("method", "EasyOCR")
                else:
                    result = extract_text_from_file(fpath, lang_hint)
                    method = result.get("method", "Tesseract")

                text = result.get("text", "")
                lang = result.get("detected_lang", "Unknown")

                if text:
                    save_extracted_text(doc["id"], case_id, text, lang, hw)
                    st.success(f"✅ {doc['filename']} — Language: {lang} | Method: {method}")
                else:
                    st.error(f"❌ No text extracted from {doc['filename']}: {result.get('error', 'Unknown error')}")

        st.success("OCR complete! Review results below.")

    # Show extracted texts
    extracted = get_extracted_texts(case_id)
    if extracted:
        st.markdown("<hr style='margin:1rem 0; border-color:#eef2f7;'>", unsafe_allow_html=True)
        st.markdown("**Extracted Text Results**")
        for ext_text in extracted:
            lang = ext_text.get("detected_lang", "Unknown")
            hw_badge = " ✍️ Handwritten" if ext_text.get("is_handwritten") else ""
            with st.expander(f"📄 {ext_text.get('filename', 'Document')} — {lang}{hw_badge}", expanded=False):
                st.markdown(f"""
                <div style="background:#f8f9fa; border-radius:8px; padding:1rem; font-size:0.85rem;
                            white-space:pre-wrap; max-height:300px; overflow-y:auto; border:1px solid #e9ecef;">
{ext_text.get('raw_text', 'No text extracted')}
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("Run OCR to extract text from uploaded documents.")


# ─── TAB: TRANSLATION ────────────────────────────────────────────────────────

def tab_translation(case_id):
    st.markdown("<div class='section-header'>🌐 Document Translation</div>", unsafe_allow_html=True)

    extracted = get_extracted_texts(case_id)
    non_english = [e for e in extracted if e.get("detected_lang", "English") not in ("English", "Unknown", "")]

    if not extracted:
        st.info("🔤 Run OCR first to extract text from documents.")
        return

    if not non_english:
        st.info("✅ All extracted text is already in English. No translation needed.")
        # Show English texts
        for et in extracted:
            with st.expander(f"📄 {et.get('filename', 'Document')} (English)", expanded=False):
                st.write(et.get("raw_text", ""))
        return

    if st.button("🌐  Translate All Non-English Documents to English", type="primary"):
        with st.spinner("Translating documents..."):
            for et in non_english:
                lang = et.get("detected_lang", "Hindi")
                result = translate_to_english(et.get("raw_text", ""), lang)
                if result.get("translated_text"):
                    save_translation(
                        et["id"], case_id,
                        et["raw_text"],
                        result["translated_text"],
                        lang
                    )
                    st.success(f"✅ {et.get('filename', 'Document')} — Translated from {lang}")
                else:
                    st.error(f"❌ Translation failed for {et.get('filename', 'Document')}: {result.get('error')}")
        st.success("Translation complete!")

    # Show side-by-side translations
    translations = get_translations(case_id)
    if translations:
        st.markdown("<hr style='margin:1rem 0; border-color:#eef2f7;'>", unsafe_allow_html=True)
        for trans in translations:
            with st.expander(f"🌐 {trans.get('filename', 'Document')} — {trans.get('source_lang', '?')} → English", expanded=True):
                left_col, right_col = st.columns(2)
                with left_col:
                    st.markdown(f"**Original ({trans.get('source_lang', 'Unknown')})**")
                    st.markdown(f"""
                    <div style="background:#fff8f0; border-radius:8px; padding:1rem; font-size:0.85rem;
                                white-space:pre-wrap; max-height:280px; overflow-y:auto; border:1px solid #ffe0b2;">
{trans.get('original_text', '')}
                    </div>
                    """, unsafe_allow_html=True)
                with right_col:
                    st.markdown("**Translated (English)**")
                    st.markdown(f"""
                    <div style="background:#f0f8ff; border-radius:8px; padding:1rem; font-size:0.85rem;
                                white-space:pre-wrap; max-height:280px; overflow-y:auto; border:1px solid #b3d9ff;">
{trans.get('translated_text', '')}
                    </div>
                    """, unsafe_allow_html=True)


# ─── TAB: AI EXTRACTION ──────────────────────────────────────────────────────

def tab_ai_extraction(case_id):
    st.markdown("<div class='section-header'>🤖 AI Information Extraction</div>", unsafe_allow_html=True)

    api_key = get_api_key()
    provider = st.session_state.get("api_provider", "anthropic")

    if not api_key:
        st.warning("⚠️ No API key configured. Running in demo mode (regex extraction). Add your key in Settings for full AI extraction.")

    # Gather all translated/extracted text
    translations = get_translations(case_id)
    extracted = get_extracted_texts(case_id)

    full_text = ""
    if translations:
        full_text = "\n\n---\n\n".join([t.get("translated_text", "") for t in translations])
    elif extracted:
        full_text = "\n\n---\n\n".join([e.get("raw_text", "") for e in extracted])

    if not full_text:
        st.info("🌐 Translate your documents first (or run OCR for English documents).")
        return

    # Show text to be analyzed
    with st.expander("📄 Text to be analyzed by AI", expanded=False):
        st.text_area("", value=truncate_text(full_text, 1000) + ("..." if len(full_text) > 1000 else ""),
                     height=150, disabled=True, label_visibility="collapsed")

    if st.button("🤖  Extract Information with AI", type="primary", use_container_width=True):
        with st.spinner("AI is extracting structured information..."):
            result = extract_information(full_text, api_key, provider)

        if result["success"]:
            fields = result["fields"]
            # Save to form_data and case
            form_payload = {k: v for k, v in fields.items() if v}
            form_payload["raw_json"] = result["raw_json"]
            save_form_data(case_id, form_payload)

            # Update case claimant name if found
            if fields.get("claimant_name"):
                update_case(case_id, claimant_name=fields["claimant_name"])
            if fields.get("policy_number"):
                update_case(case_id, policy_number=fields["policy_number"])

            st.success(f"✅ Extraction complete! Method: {result['method']}")
            st.rerun()
        else:
            st.error(f"❌ Extraction failed: {result.get('error')}")

    # Show current extracted data
    form_data = get_form_data(case_id)
    if form_data:
        st.markdown("<hr style='margin:1rem 0; border-color:#eef2f7;'>", unsafe_allow_html=True)
        st.markdown("**Extracted Information**")

        field_groups = [
            ("👤 Claimant Details", [
                ("Claimant Name", form_data.get("claimant_name")),
                ("Age", form_data.get("age")),
                ("Address", form_data.get("address")),
                ("Phone", form_data.get("phone")),
            ]),
            ("📋 Policy & Claim", [
                ("Policy Number", form_data.get("policy_number")),
                ("Claim Amount", form_data.get("claim_amount")),
                ("Insurance Company", form_data.get("insurance_company")),
            ]),
            ("🏥 Medical Details", [
                ("Hospital Name", form_data.get("hospital_name")),
                ("Hospital Address", form_data.get("hospital_address")),
                ("Diagnosis", form_data.get("diagnosis")),
                ("Doctor Name", form_data.get("doctor_name")),
            ]),
            ("📅 Dates", [
                ("Incident Date", form_data.get("incident_date")),
                ("Admission Date", form_data.get("admission_date")),
                ("Discharge Date", form_data.get("discharge_date")),
                ("Treatment Duration", form_data.get("treatment_duration")),
            ]),
        ]

        for group_title, fields_list in field_groups:
            populated = [(k, v) for k, v in fields_list if v]
            if populated:
                st.markdown(f"**{group_title}**")
                g_cols = st.columns(2)
                for i, (label, value) in enumerate(populated):
                    with g_cols[i % 2]:
                        st.markdown(f"""
                        <div style="background:#f7f9fc; border-radius:8px; padding:0.6rem 0.9rem; margin-bottom:0.5rem; border:1px solid #eef2f7;">
                            <div style="font-size:0.7rem; text-transform:uppercase; letter-spacing:0.08em; color:#888; margin-bottom:0.2rem;">{label}</div>
                            <div style="font-size:0.9rem; font-weight:600; color:#1a1a2e;">{value}</div>
                        </div>
                        """, unsafe_allow_html=True)

        if form_data.get("suspicious_indicators"):
            st.markdown("**⚠️ Suspicious Indicators**")
            st.warning(form_data["suspicious_indicators"])


# ─── TAB: INVESTIGATION FORM ─────────────────────────────────────────────────

def tab_investigation_form(case_id, case):
    st.markdown("<div class='section-header'>📝 Investigation Form</div>", unsafe_allow_html=True)
    st.info("All fields are pre-filled from AI extraction. Review and edit as needed before saving.")

    fd = get_form_data(case_id)

    with st.form("investigation_form"):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Claimant Information**")
            claimant_name  = st.text_input("Claimant Name", value=fd.get("claimant_name", "") or "")
            age            = st.text_input("Age", value=fd.get("age", "") or "")
            phone          = st.text_input("Phone Number", value=fd.get("phone", "") or "")
            address        = st.text_area("Address", value=fd.get("address", "") or "", height=80)

            st.markdown("**Policy Details**")
            policy_number  = st.text_input("Policy Number", value=fd.get("policy_number", "") or "")
            claim_amount   = st.text_input("Claim Amount", value=fd.get("claim_amount", "") or "")
            insurance_co   = st.text_input("Insurance Company", value=fd.get("insurance_company", "") or "")

        with col2:
            st.markdown("**Medical Information**")
            hospital_name  = st.text_input("Hospital Name", value=fd.get("hospital_name", "") or "")
            hospital_addr  = st.text_input("Hospital Address", value=fd.get("hospital_address", "") or "")
            diagnosis      = st.text_input("Diagnosis", value=fd.get("diagnosis", "") or "")
            doctor_name    = st.text_input("Treating Doctor", value=fd.get("doctor_name", "") or "")

            st.markdown("**Key Dates**")
            incident_date  = st.text_input("Incident Date", value=fd.get("incident_date", "") or "")
            admission_date = st.text_input("Admission Date", value=fd.get("admission_date", "") or "")
            discharge_date = st.text_input("Discharge Date", value=fd.get("discharge_date", "") or "")

        st.markdown("**Investigation Notes**")
        investigator_notes = st.text_area("Investigator Notes", value=fd.get("investigator_notes", "") or "",
                                           height=100, placeholder="Add your investigation findings and observations here...")
        suspicious = st.text_area("Suspicious Indicators", value=fd.get("suspicious_indicators", "") or "",
                                   height=80, placeholder="Document any red flags or inconsistencies found...")

        saved = st.form_submit_button("💾  Save Investigation Form", use_container_width=True, type="primary")

        if saved:
            data = {
                "claimant_name": claimant_name, "age": age, "phone": phone,
                "address": address, "policy_number": policy_number, "claim_amount": claim_amount,
                "insurance_company": insurance_co, "hospital_name": hospital_name,
                "hospital_address": hospital_addr, "diagnosis": diagnosis, "doctor_name": doctor_name,
                "incident_date": incident_date, "admission_date": admission_date,
                "discharge_date": discharge_date, "investigator_notes": investigator_notes,
                "suspicious_indicators": suspicious,
            }
            save_form_data(case_id, data)
            if claimant_name:
                update_case(case_id, claimant_name=claimant_name)
            if policy_number:
                update_case(case_id, policy_number=policy_number)
            st.success("✅ Investigation form saved successfully!")


# ─── TAB: AI REPORT ──────────────────────────────────────────────────────────

def tab_report(case_id, case):
    st.markdown("<div class='section-header'>📊 AI Investigation Report</div>", unsafe_allow_html=True)

    api_key = get_api_key()
    provider = st.session_state.get("api_provider", "anthropic")
    fd = get_form_data(case_id)
    fraud = get_latest_fraud_score(case_id)
    timeline_data = get_latest_report(case_id)
    tl_events = json.loads(timeline_data.get("timeline_json", "[]")) if timeline_data.get("timeline_json") else []

    if not fd:
        st.info("📝 Complete the Investigation Form first.")
        return

    if st.button("✍️  Generate AI Report", type="primary", use_container_width=True):
        with st.spinner("Generating investigation report..."):
            result = generate_report(fd, fraud, tl_events, api_key, provider)
            save_report(case_id, result["report_text"], json.dumps(result["key_points"]),
                       json.dumps(tl_events))
            st.session_state[f"report_{case_id}"] = result
        st.success(f"✅ Report generated! Method: {result['method']}")

    # Load saved report
    report_data = st.session_state.get(f"report_{case_id}") or {}
    if not report_data:
        saved_report = get_latest_report(case_id)
        if saved_report:
            report_data = {
                "report_text": saved_report.get("report_text", ""),
                "key_points": json.loads(saved_report.get("key_points", "[]")) if saved_report.get("key_points") else [],
            }

    if report_data:
        col_r, col_kp = st.columns([2, 1])

        with col_r:
            st.markdown("**Investigation Report** *(editable)*")
            edited_report = st.text_area(
                "", value=report_data.get("report_text", ""),
                height=400, label_visibility="collapsed",
                key=f"report_text_{case_id}"
            )
            if st.button("💾 Save Edited Report"):
                save_report(case_id, edited_report,
                           json.dumps(report_data.get("key_points", [])),
                           json.dumps(tl_events))
                st.success("Report saved!")

        with col_kp:
            kp = report_data.get("key_points", [])
            if kp:
                st.markdown("**Key Investigation Points**")
                for point in kp:
                    st.markdown(f"""
                    <div style="background:#f0fff4; border-left:3px solid #27ae60; padding:0.5rem 0.75rem;
                                margin-bottom:0.4rem; border-radius:0 6px 6px 0; font-size:0.85rem;">
                        ✓ {point}
                    </div>
                    """, unsafe_allow_html=True)


# ─── TAB: FRAUD RISK ─────────────────────────────────────────────────────────

def tab_fraud_risk(case_id, case):
    st.markdown("<div class='section-header'>🚨 Fraud Risk Assessment</div>", unsafe_allow_html=True)

    api_key = get_api_key()
    provider = st.session_state.get("api_provider", "anthropic")
    fd = get_form_data(case_id)

    if not fd:
        st.info("📝 Complete the Investigation Form first.")
        return

    if st.button("🔍  Run Fraud Risk Assessment", type="primary", use_container_width=True):
        with st.spinner("Analyzing case for fraud risk indicators..."):
            result = assess_fraud_risk(dict(case), fd, api_key, provider)
            save_fraud_score(case_id, result["score"], result["risk_level"],
                           result["explanation"], json.dumps(result.get("indicators", [])))
            st.session_state[f"fraud_{case_id}"] = result
        st.success(f"✅ Assessment complete! Method: {result['method']}")

    # Load result
    fraud_result = st.session_state.get(f"fraud_{case_id}")
    if not fraud_result:
        saved = get_latest_fraud_score(case_id)
        if saved:
            fraud_result = {
                "score": saved.get("score", 0),
                "risk_level": saved.get("risk_level", ""),
                "explanation": saved.get("explanation", ""),
                "indicators": json.loads(saved.get("indicators", "[]")) if saved.get("indicators") else [],
            }

    if fraud_result:
        score = fraud_result.get("score", 0)
        risk_level = fraud_result.get("risk_level", "Unknown")
        color = get_risk_color(risk_level)
        emoji = get_risk_emoji(risk_level)

        # Score display
        gauge_pct = score
        col_score, col_detail = st.columns([1, 2])

        with col_score:
            st.markdown(f"""
            <div style="text-align:center; background:white; border-radius:16px; padding:2rem 1.5rem;
                        box-shadow:0 4px 20px rgba(0,0,0,0.08); border:2px solid {color}30;">
                <div style="font-size:3.5rem; font-weight:900; color:{color}; line-height:1;">{score}</div>
                <div style="font-size:0.75rem; color:#888; text-transform:uppercase; letter-spacing:0.1em; margin-top:0.25rem;">Risk Score / 100</div>
                <div style="margin:1rem 0; background:#f0f4f8; border-radius:20px; height:10px; overflow:hidden;">
                    <div style="width:{gauge_pct}%; height:100%; background:{color}; border-radius:20px; transition:width 0.5s;"></div>
                </div>
                <div style="font-size:1.1rem; font-weight:800; color:{color};">{emoji} {risk_level}</div>
            </div>
            """, unsafe_allow_html=True)

        with col_detail:
            st.markdown("**Assessment Summary**")
            st.markdown(f"""
            <div style="background:#f8f9fa; border-radius:10px; padding:1rem 1.25rem;
                        border-left:4px solid {color}; margin-bottom:1rem; font-size:0.9rem;">
                {fraud_result.get('explanation', '')}
            </div>
            """, unsafe_allow_html=True)

            indicators = fraud_result.get("indicators", [])
            if indicators:
                st.markdown("**Risk Indicators**")
                for ind in indicators:
                    ind_color = "#e74c3c" if score > 65 else ("#f39c12" if score > 30 else "#27ae60")
                    st.markdown(f"""
                    <div style="background:white; border:1px solid {ind_color}30; border-left:3px solid {ind_color};
                                border-radius:0 8px 8px 0; padding:0.5rem 0.75rem; margin-bottom:0.4rem; font-size:0.85rem;">
                        {'🔴' if score>65 else '🟡' if score>30 else '🟢'} {ind}
                    </div>
                    """, unsafe_allow_html=True)

            recs = fraud_result.get("recommendations", [])
            if recs:
                st.markdown("**Recommendations**")
                for rec in recs:
                    st.markdown(f"→ {rec}")


# ─── TAB: TIMELINE ────────────────────────────────────────────────────────────

def tab_timeline(case_id):
    st.markdown("<div class='section-header'>📅 Investigation Timeline</div>", unsafe_allow_html=True)

    api_key = get_api_key()
    provider = st.session_state.get("api_provider", "anthropic")
    fd = get_form_data(case_id)
    extracted = get_extracted_texts(case_id)
    doc_text = " ".join([e.get("raw_text", "") for e in extracted]) if extracted else ""

    if not fd:
        st.info("📝 Complete the Investigation Form first.")
        return

    if st.button("📅  Generate Timeline", type="primary", use_container_width=True):
        with st.spinner("Building timeline of events..."):
            result = generate_timeline(fd, doc_text, api_key, provider)
            events = result.get("events", [])
            # Save to report table
            saved_report = get_latest_report(case_id)
            if saved_report:
                save_report(case_id,
                           saved_report.get("report_text", ""),
                           saved_report.get("key_points", ""),
                           json.dumps(events))
            else:
                save_report(case_id, "", "", json.dumps(events))
            st.session_state[f"timeline_{case_id}"] = events
        st.success(f"✅ Timeline generated! Method: {result['method']}")

    # Load timeline
    tl_events = st.session_state.get(f"timeline_{case_id}")
    if not tl_events:
        saved = get_latest_report(case_id)
        if saved and saved.get("timeline_json"):
            try:
                tl_events = json.loads(saved["timeline_json"])
            except Exception:
                tl_events = []

    if tl_events:
        st.markdown("<hr style='margin:1rem 0; border-color:#eef2f7;'>", unsafe_allow_html=True)

        # Category legend
        cat_colors = {
            "incident": "#e74c3c", "medical": "#3498db",
            "claim": "#27ae60", "investigation": "#9b59b6", "other": "#95a5a6"
        }

        for i, event in enumerate(tl_events):
            cat = event.get("category", "other").lower()
            cat_color = cat_colors.get(cat, "#95a5a6")
            cat_emoji = get_timeline_category_emoji(cat)
            is_last = i == len(tl_events) - 1

            st.markdown(f"""
            <div style="display:flex; gap:1.5rem; padding:0.75rem 0;">
                <div style="display:flex; flex-direction:column; align-items:center; min-width:20px;">
                    <div style="width:14px; height:14px; border-radius:50%; background:{cat_color}; margin-top:4px; flex-shrink:0; border:2px solid white; box-shadow:0 0 0 2px {cat_color}40;"></div>
                    {"" if is_last else f'<div style="width:2px; background:{cat_color}30; flex:1; margin-top:4px;"></div>'}
                </div>
                <div style="flex:1; padding-bottom:{'0' if is_last else '0.5rem'};">
                    <div style="font-size:0.8rem; color:{cat_color}; font-weight:700; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:0.1rem;">{event.get('date', 'Date unknown')}</div>
                    <div style="font-size:0.92rem; color:#1a1a2e; font-weight:500;">{cat_emoji} {event.get('event', '')}</div>
                    <div style="font-size:0.72rem; color:#aaa; margin-top:0.1rem; text-transform:capitalize;">{cat}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Click 'Generate Timeline' to automatically build the investigation timeline from case data.")


# ─── TAB: EXPORT ─────────────────────────────────────────────────────────────

def tab_export(case_id, case):
    st.markdown("<div class='section-header'>📤 Export Investigation Report</div>", unsafe_allow_html=True)

    fd = get_form_data(case_id)
    fraud = get_latest_fraud_score(case_id)
    saved_report = get_latest_report(case_id)
    tl_events = []
    if saved_report and saved_report.get("timeline_json"):
        try:
            tl_events = json.loads(saved_report["timeline_json"])
        except Exception:
            pass

    kp_list = []
    if saved_report and saved_report.get("key_points"):
        try:
            kp_list = json.loads(saved_report["key_points"])
        except Exception:
            kp_list = [saved_report["key_points"]]

    report_text = saved_report.get("report_text", "") if saved_report else ""

    if not fd:
        st.info("📝 Complete the Investigation Form first, then generate a report.")
        return

    st.markdown("""
    <div style="background:#f7f9fc; border-radius:12px; padding:1.5rem; margin-bottom:1.5rem; border:1px solid #eef2f7;">
        <div style="font-weight:700; margin-bottom:1rem; color:#0f3460;">Export Checklist</div>
    """, unsafe_allow_html=True)

    checks = [
        ("Investigation Form", bool(fd)),
        ("AI Report", bool(report_text)),
        ("Fraud Risk Score", bool(fraud)),
        ("Timeline", bool(tl_events)),
    ]
    check_cols = st.columns(len(checks))
    for col, (label, done) in zip(check_cols, checks):
        with col:
            icon = "✅" if done else "⚠️"
            color = "#27ae60" if done else "#f39c12"
            st.markdown(f"<div style='text-align:center; font-size:0.85rem; color:{color};'>{icon}<br>{label}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    col_pdf, col_json = st.columns(2)

    with col_pdf:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown("**📄 PDF Export**")
        st.write("Professional PDF report with all case details, fraud score, and timeline.")
        if st.button("📄  Export as PDF", use_container_width=True, type="primary"):
            output_path = get_export_path(case_id, "pdf")
            with st.spinner("Generating PDF..."):
                success = export_pdf(
                    dict(case), fd or {}, report_text, kp_list,
                    dict(fraud) if fraud else {}, tl_events, output_path
                )
            if success and Path(output_path).exists():
                with open(output_path, "rb") as f:
                    st.download_button(
                        "⬇️  Download PDF",
                        data=f.read(),
                        file_name=f"{case_id}_report.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                    )
                st.success("PDF ready for download!")
            else:
                st.error("PDF generation failed. Ensure ReportLab is installed.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_json:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown("**📋 JSON Export**")
        st.write("Complete case data in JSON format for integration with other systems.")
        if st.button("📋  Export as JSON", use_container_width=True):
            output_path = get_export_path(case_id, "json")
            success = export_json(
                dict(case), fd or {}, report_text, kp_list,
                dict(fraud) if fraud else {}, tl_events, output_path
            )
            if success and Path(output_path).exists():
                with open(output_path, "r") as f:
                    st.download_button(
                        "⬇️  Download JSON",
                        data=f.read(),
                        file_name=f"{case_id}_report.json",
                        mime="application/json",
                        use_container_width=True,
                    )
                st.success("JSON ready for download!")
            else:
                st.error("JSON export failed.")
        st.markdown("</div>", unsafe_allow_html=True)


# ─── HELP AGENT PAGE ─────────────────────────────────────────────────────────

def page_help_agent():
    """Full-page Help Agent with conversation history."""
    st.markdown("""
    <div style="display:flex; align-items:center; gap:0.75rem; margin-bottom:0.25rem;">
        <div style="font-size:1.75rem; font-weight:800; color:#0f3460; letter-spacing:-0.5px;">🤖 AI Help Agent</div>
    </div>
    <div style="color:#666; font-size:0.9rem; margin-bottom:1.5rem;">
        Ask me anything about InvestiAI, investigation techniques, fraud detection, or insurance.
    </div>
    """, unsafe_allow_html=True)

    api_key = get_api_key()

    # Mode badge
    from local_ai import is_ollama_running, get_best_model
    _ollama_ok = is_ollama_running()
    _model     = get_best_model() if _ollama_ok else None
    if _ollama_ok and _model:
        st.markdown(f'<div style="display:inline-block;background:#e8f5e9;color:#2e7d32;font-size:.78rem;font-weight:700;padding:3px 12px;border-radius:20px;margin-bottom:1rem">🟢 Local AI Active — {_model} (Free, no API key needed)</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="display:inline-block;background:#fff3e0;color:#e65100;font-size:.78rem;font-weight:700;padding:3px 12px;border-radius:20px;margin-bottom:1rem">⚡ Demo Mode — Install Ollama in ⚙️ Settings for free AI</div>', unsafe_allow_html=True)

    # Get current case context
    context = {}
    if st.session_state.current_case_id:
        case = get_case(st.session_state.current_case_id)
        fd = get_form_data(st.session_state.current_case_id)
        fraud = get_latest_fraud_score(st.session_state.current_case_id)
        if case:
            context["case_id"] = case.get("case_id")
            context["claimant_name"] = case.get("claimant_name")
        if fd:
            context["diagnosis"] = fd.get("diagnosis")
        if fraud:
            context["fraud_score"] = f"{fraud.get('score')}/100 {fraud.get('risk_level')}"

    chat_col, help_col = st.columns([2, 1])

    with chat_col:
        # Chat history display
        history = st.session_state.agent_history
        chat_container = st.container()

        with chat_container:
            if not history:
                st.markdown("""
                <div style="text-align:center; padding:2.5rem 1rem; background:#f8fafc;
                            border-radius:16px; border:2px dashed #d0dce8; margin-bottom:1.5rem;">
                    <div style="font-size:2.5rem; margin-bottom:0.75rem;">🤖</div>
                    <div style="font-size:1rem; font-weight:700; color:#0f3460; margin-bottom:0.5rem;">
                        Hello! I'm your InvestiAI Assistant.
                    </div>
                    <div style="font-size:0.88rem; color:#666; max-width:380px; margin:0 auto;">
                        Ask me about app features, investigation techniques, fraud patterns,
                        or any insurance question. I'm here to help!
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                for turn in history:
                    _render_chat_message(turn["role"], turn["content"])

        # Quick question chips — only show if no history
        if not history:
            st.markdown("**Try asking:**")
            quick_qs = get_quick_questions(4)
            q_cols = st.columns(2)
            for i, q in enumerate(quick_qs):
                with q_cols[i % 2]:
                    if st.button(q, key=f"quick_{i}", use_container_width=True):
                        _process_agent_message(q, api_key, context)
                        st.rerun()

        # Input area
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        with st.form("agent_chat_form", clear_on_submit=True):
            input_col, btn_col = st.columns([5, 1])
            with input_col:
                user_input = st.text_input(
                    "", placeholder="Ask me anything about InvestiAI or insurance investigation...",
                    label_visibility="collapsed", key="agent_input_field"
                )
            with btn_col:
                submitted = st.form_submit_button("Send →", use_container_width=True, type="primary")

        if submitted and user_input:
            with st.spinner("Thinking..."):
                _process_agent_message(user_input, api_key, context)
            st.rerun()

        # Clear history button
        if history:
            if st.button("🗑️  Clear Conversation", key="clear_agent_history"):
                st.session_state.agent_history = []
                st.rerun()

    with help_col:
        _render_agent_topics_panel()


def _render_chat_message(role: str, content: str):
    """Render a single chat message bubble."""
    if role == "user":
        st.markdown(f"""
        <div style="display:flex; justify-content:flex-end; margin-bottom:0.75rem;">
            <div style="background:#0f3460; color:white; border-radius:16px 16px 4px 16px;
                        padding:0.65rem 1rem; max-width:80%; font-size:0.88rem; line-height:1.5;">
                {content}
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="display:flex; gap:0.75rem; margin-bottom:0.75rem; align-items:flex-start;">
            <div style="background:#0f3460; color:white; border-radius:50%; width:32px; height:32px;
                        display:flex; align-items:center; justify-content:center;
                        font-size:0.85rem; flex-shrink:0; margin-top:2px;">🤖</div>
            <div style="background:#f0f4f8; border-radius:4px 16px 16px 16px;
                        padding:0.65rem 1rem; max-width:85%; font-size:0.88rem;
                        line-height:1.6; border:1px solid #e0e8f0;">
                {content.replace(chr(10), '<br>')}
            </div>
        </div>
        """, unsafe_allow_html=True)


def _process_agent_message(message: str, api_key: str, context: dict):
    """Call agent and append exchange to history."""
    history = st.session_state.agent_history
    response = ask_agent(message, history, api_key, context)
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": response})
    st.session_state.agent_history = history


def _render_agent_topics_panel():
    """Right-side panel showing what the agent knows about."""
    st.markdown("""
    <div style="background:white; border-radius:12px; padding:1.25rem 1.5rem;
                box-shadow:0 2px 12px rgba(15,52,96,0.08); border:1px solid #eef2f7;">
        <div style="font-size:0.72rem; font-weight:700; text-transform:uppercase;
                    letter-spacing:0.1em; color:#0f3460; margin-bottom:1rem; padding-bottom:0.5rem;
                    border-bottom:2px solid #e8f0fe;">What I Can Help With</div>
    """, unsafe_allow_html=True)

    topics = [
        ("📱", "App Guidance",
         ["Creating & managing cases", "Uploading documents", "Running OCR", "Translating Hindi/Gujarati",
          "AI information extraction", "Exporting PDF reports", "Adding API keys"]),
        ("🔍", "Investigation Tips",
         ["Document verification", "Field investigation", "Claimant interviews", "Hospital verification",
          "Building a case file", "IRDAI compliance"]),
        ("🚨", "Fraud Detection",
         ["Common fraud patterns", "Document fraud red flags", "Medical fraud indicators",
          "When to escalate", "Interpreting fraud scores"]),
        ("❓", "Insurance Q&A",
         ["Insurance terminology", "Policy types & coverage", "Claim processing", "Waiting periods",
          "IRDAI regulations"]),
    ]

    for icon, title, items in topics:
        st.markdown(f"""
        <div style="margin-bottom:1rem;">
            <div style="font-weight:700; font-size:0.88rem; color:#1a1a2e; margin-bottom:0.35rem;">
                {icon} {title}
            </div>
            {"".join(f'<div style="font-size:0.78rem; color:#666; padding:0.15rem 0 0.15rem 1rem;">· {item}</div>' for item in items)}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


# ─── FLOATING CHAT BUBBLE ─────────────────────────────────────────────────────

def render_floating_agent():
    """
    Renders a floating chat bubble panel that appears on all pages.
    Toggled by the sidebar button or the floating button.
    Uses Streamlit expander for Windows compatibility (no JavaScript required).
    """
    if not st.session_state.agent_open:
        return

    api_key = get_api_key()
    context = {}
    if st.session_state.current_case_id:
        case = get_case(st.session_state.current_case_id)
        fd = get_form_data(st.session_state.current_case_id)
        if case:
            context["case_id"] = case.get("case_id")
            context["claimant_name"] = case.get("claimant_name")
        if fd:
            context["diagnosis"] = fd.get("diagnosis")

    st.markdown("<hr style='margin:2rem 0 0.5rem; border-color:#eef2f7;'>", unsafe_allow_html=True)
    st.markdown("""
    <div style="background:linear-gradient(135deg,#0f3460,#16213e); color:white;
                border-radius:12px 12px 0 0; padding:0.75rem 1.25rem;
                display:flex; align-items:center; gap:0.75rem;">
        <span style="font-size:1.2rem;">🤖</span>
        <span style="font-weight:700; font-size:0.95rem;">InvestiAI Help Agent</span>
        <span style="margin-left:auto; font-size:0.72rem; opacity:0.7;">Always here to help</span>
    </div>
    """, unsafe_allow_html=True)

    bubble_container = st.container()
    with bubble_container:
        history = st.session_state.agent_history

        # Message display — last 6 turns
        msg_html = ""
        if not history:
            msg_html = """<div style='text-align:center; color:#aaa; padding:1.5rem; font-size:0.85rem;'>
                👋 Hi! Ask me anything about InvestiAI.<br>
                I can help with app features, investigation tips, and fraud detection.
            </div>"""
        else:
            for turn in history[-6:]:
                if turn["role"] == "user":
                    msg_html += f"""
                    <div style="display:flex; justify-content:flex-end; margin-bottom:0.5rem;">
                        <div style="background:#0f3460; color:white; border-radius:12px 12px 2px 12px;
                                    padding:0.5rem 0.85rem; max-width:85%; font-size:0.82rem;">
                            {turn['content']}
                        </div>
                    </div>"""
                else:
                    short = turn["content"][:300] + ("…" if len(turn["content"]) > 300 else "")
                    msg_html += f"""
                    <div style="display:flex; gap:0.5rem; margin-bottom:0.5rem; align-items:flex-start;">
                        <div style="background:#0f3460; color:white; border-radius:50%;
                                    min-width:26px; height:26px; display:flex; align-items:center;
                                    justify-content:center; font-size:0.75rem; margin-top:2px;">🤖</div>
                        <div style="background:#f0f4f8; border-radius:2px 12px 12px 12px;
                                    padding:0.5rem 0.85rem; max-width:85%; font-size:0.82rem;
                                    line-height:1.5; border:1px solid #e0e8f0;">
                            {short.replace(chr(10),'<br>')}
                        </div>
                    </div>"""

        st.markdown(f"""
        <div style="background:#fafbfc; border:1px solid #e0e8f0; border-top:none;
                    padding:1rem; min-height:180px; max-height:280px; overflow-y:auto;
                    border-radius:0 0 0 0;">
            {msg_html}
        </div>
        """, unsafe_allow_html=True)

        # Quick chips (first time)
        if not history:
            quick_qs = get_quick_questions(3)
            chip_cols = st.columns(3)
            for i, q in enumerate(quick_qs):
                with chip_cols[i]:
                    if st.button(q[:28] + ("…" if len(q) > 28 else ""),
                                 key=f"bubble_quick_{i}", use_container_width=True):
                        with st.spinner(""):
                            _process_agent_message(q, api_key, context)
                        st.rerun()

        # Input form
        with st.form("bubble_form", clear_on_submit=True):
            bubble_input = st.text_input(
                "", placeholder="Ask a question...",
                label_visibility="collapsed", key="bubble_input"
            )
            b_col1, b_col2, b_col3 = st.columns([4, 1, 1])
            with b_col1:
                b_send = st.form_submit_button("Send", use_container_width=True, type="primary")
            with b_col2:
                b_full = st.form_submit_button("Full →", use_container_width=True)
            with b_col3:
                b_close = st.form_submit_button("✕", use_container_width=True)

        if b_send and bubble_input:
            with st.spinner(""):
                _process_agent_message(bubble_input, api_key, context)
            st.rerun()
        if b_full:
            nav_to("help_agent")
        if b_close:
            st.session_state.agent_open = False
            st.rerun()

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)



# ── AI HELP AGENT PAGE ────────────────────────────────────────────────────────

def page_help_agent():
    cid     = st.session_state.current_case_id
    api_key = get_api_key()
    history = st.session_state.agent_history

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="display:flex;align-items:center;gap:.75rem;margin-bottom:.25rem">
      <div style="font-size:1.75rem;font-weight:800;color:#0f3460;letter-spacing:-.5px">🤖 AI Help Agent</div>
    </div>
    <div style="color:#666;font-size:.9rem;margin-bottom:1rem">
      I can <b>read your case</b>, <b>remember our conversation</b>, and <b>take actions</b> for you.
    </div>
    """, unsafe_allow_html=True)

    # ── Mode badge ────────────────────────────────────────────────────────────
    try:
        from local_ai import is_ollama_running as _or, get_best_model as _gm
        _ollama_ok2 = _or(); _model2 = _gm() if _ollama_ok2 else None
    except: _ollama_ok2 = False; _model2 = None
    if _ollama_ok2 and _model2:
        st.markdown(f'<div style="display:inline-block;background:#e8f5e9;color:#2e7d32;font-size:.78rem;font-weight:700;padding:3px 12px;border-radius:20px;margin-bottom:1rem">🟢 Local AI Active — {_model2} (Free!)</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="display:inline-block;background:#fff3e0;color:#e65100;font-size:.78rem;font-weight:700;padding:3px 12px;border-radius:20px;margin-bottom:1rem">⚡ Demo Mode — Install Ollama (free) in ⚙️ Settings → Local AI Setup</div>', unsafe_allow_html=True)

    # ── Active case pill ──────────────────────────────────────────────────────
    if cid:
        case = get_case(cid)
        name = case.get("claimant_name","?") if case else "?"
        pill = ('<div style="display:inline-block;background:#e8f0fe;color:#0f3460;'
                'font-size:.8rem;font-weight:600;padding:4px 14px;border-radius:20px;'
                'margin-bottom:1rem;border:1px solid #c5d8f7">'
                f'📁 Active case: {cid} — {name}</div>')
        st.markdown(pill, unsafe_allow_html=True)
    else:
        st.info("💡 Open a case from the dashboard to let the agent read and act on it.")

    # ── Layout ────────────────────────────────────────────────────────────────
    chat_col, help_col = st.columns([2, 1])

    with chat_col:
        # ── Chat history ──────────────────────────────────────────────────────
        if not history:
            st.markdown("""
            <div style="text-align:center;padding:2rem 1rem;background:#f8fafc;
                        border-radius:16px;border:2px dashed #d0dce8;margin-bottom:1.5rem">
              <div style="font-size:2.5rem;margin-bottom:.75rem">🤖</div>
              <div style="font-size:1rem;font-weight:700;color:#0f3460;margin-bottom:.5rem">
                Hello! I'm your InvestiAI Assistant.
              </div>
              <div style="font-size:.88rem;color:#666;max-width:400px;margin:0 auto">
                Ask me anything, or tell me to take an action on your case — like
                <i>"retranslate the documents"</i>, <i>"change diagnosis to typhoid"</i>,
                or <i>"show me the case summary"</i>.
              </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            for turn in history:
                _render_bubble(turn["role"], turn["content"])

        # ── Quick chips ───────────────────────────────────────────────────────
        if not history:
            st.markdown("**Try asking:**")
            chips = get_quick_questions(cid, 4)
            ccols = st.columns(2)
            for i, q in enumerate(chips):
                with ccols[i % 2]:
                    if st.button(q, key=f"chip_{i}", use_container_width=True):
                        with st.spinner("Working…"):
                            resp, new_hist = ask_agent(q, history, cid, api_key)
                        st.session_state.agent_history = new_hist
                        st.rerun()

        # ── Input form ────────────────────────────────────────────────────────
        st.markdown("<div style='height:.75rem'></div>", unsafe_allow_html=True)
        with st.form("agent_form", clear_on_submit=True):
            ic, bc = st.columns([6, 1])
            with ic:
                user_input = st.text_input(
                    "", placeholder="Ask a question or give a command…",
                    label_visibility="collapsed", key="agent_text_input",
                )
            with bc:
                sent = st.form_submit_button("Send", use_container_width=True, type="primary")

        if sent and user_input:
            with st.spinner("Thinking…"):
                resp, new_hist = ask_agent(user_input, history, cid, api_key)
            st.session_state.agent_history = new_hist
            st.rerun()

        # ── Clear button ──────────────────────────────────────────────────────
        if history:
            if st.button("🗑️  Clear conversation", key="clear_hist"):
                st.session_state.agent_history = []
                st.rerun()

    # ── Right panel ───────────────────────────────────────────────────────────
    with help_col:
        _render_help_panel(cid)


def _render_bubble(role: str, content: str):
    if role == "user":
        st.markdown(f"""
        <div style="display:flex;justify-content:flex-end;margin-bottom:.75rem">
          <div style="background:#0f3460;color:white;border-radius:16px 16px 4px 16px;
                      padding:.65rem 1rem;max-width:82%;font-size:.88rem;line-height:1.55">
            {content}
          </div>
        </div>""", unsafe_allow_html=True)
    else:
        # Render markdown in assistant messages via st.markdown
        st.markdown(f"""
        <div style="display:flex;gap:.75rem;margin-bottom:.75rem;align-items:flex-start">
          <div style="background:#0f3460;color:white;border-radius:50%;width:32px;height:32px;
                      display:flex;align-items:center;justify-content:center;
                      font-size:.85rem;flex-shrink:0;margin-top:2px">🤖</div>
          <div style="background:#f0f4f8;border-radius:4px 16px 16px 16px;
                      padding:.65rem 1rem;max-width:88%;font-size:.88rem;
                      line-height:1.6;border:1px solid #e0e8f0">
            {content.replace(chr(10),"<br>")}
          </div>
        </div>""", unsafe_allow_html=True)


def _render_help_panel(cid):
    st.markdown("""<div style="background:white;border-radius:12px;padding:1.25rem 1.5rem;
      box-shadow:0 2px 12px rgba(15,52,96,.08);border:1px solid #eef2f7">
      <div style="font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.1em;
                  color:#0f3460;margin-bottom:1rem;padding-bottom:.5rem;border-bottom:2px solid #e8f0fe">
        What I Can Do
      </div>""", unsafe_allow_html=True)

    sections = [
        ("⚡", "Take Actions on Your Case",
         ["Retranslate documents", "Re-run OCR", "Re-extract information",
          "Update any form field", "Re-assess fraud risk",
          "Regenerate the report", "Rebuild the timeline",
          "Show full case summary"]),
        ("📖", "Read Your Case",
         ["See all uploaded documents", "Read extracted OCR text",
          "Read translated text", "View all form fields",
          "Check fraud scores and indicators"]),
        ("💡", "Answer Questions",
         ["InvestiAI feature guidance", "Investigation best practices",
          "Fraud detection patterns", "IRDAI regulations & insurance terms"]),
    ]

    for icon, title, items in sections:
        st.markdown(f"""
        <div style="margin-bottom:1rem">
          <div style="font-weight:700;font-size:.88rem;color:#1a1a2e;margin-bottom:.35rem">{icon} {title}</div>
          {"".join(f'<div style="font-size:.78rem;color:#666;padding:.15rem 0 .15rem 1rem">· {item}</div>' for item in items)}
        </div>""", unsafe_allow_html=True)

    if cid:
        st.markdown(f"""
        <div style="background:#e8f0fe;border-radius:8px;padding:.6rem .9rem;margin-top:.5rem;font-size:.8rem">
          <b>Command examples:</b><br>
          <i>"Retranslate the documents"</i><br>
          <i>"Change diagnosis to typhoid"</i><br>
          <i>"Set claim amount to ₹50,000"</i><br>
          <i>"Show me the case summary"</i><br>
          <i>"Re-run fraud assessment"</i>
        </div>""", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


# ── ROUTER ────────────────────────────────────────────────────────────────────

def main():
    render_sidebar()
    page = st.session_state.get("page","dashboard")
    if   page == "dashboard":      page_dashboard()
    elif page == "new_case":       page_new_case()
    elif page == "case_workspace": page_case_workspace()
    elif page == "help_agent":     page_help_agent()
    elif page == "settings":       page_settings()
    else:                          page_dashboard()

if __name__ == "__main__":
    main()

# ── AI HELP AGENT ─────────────────────────────────────────────────────────────
def page_help_agent():
    cid     = st.session_state.current_case_id
    history = st.session_state.agent_history

    st.markdown("""
    <div style="font-size:1.75rem;font-weight:800;color:#0f3460;letter-spacing:-.5px;margin-bottom:.25rem">🤖 AI Help Agent</div>
    <div style="color:#666;font-size:.9rem;margin-bottom:1rem">I can read your case, remember our conversation, and take actions for you.</div>
    """, unsafe_allow_html=True)

    # AI status badge
    try:
        from groq_ai import is_available
        groq_ok = is_available()
    except Exception:
        groq_ok = False

    if groq_ok:
        st.markdown('<div style="display:inline-block;background:#e8f5e9;color:#2e7d32;font-size:.78rem;font-weight:700;padding:3px 12px;border-radius:20px;margin-bottom:1rem">🟢 Groq AI Active — Free, no API cost</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="display:inline-block;background:#fff3e0;color:#e65100;font-size:.78rem;font-weight:700;padding:3px 12px;border-radius:20px;margin-bottom:1rem">⚡ Demo Mode — Add free Groq key in ⚙️ Settings for full AI</div>', unsafe_allow_html=True)

    if cid:
        case = get_case(cid)
        name = case.get("claimant_name","?") if case else "?"
        pill = f'<div style="display:inline-block;background:#e8f0fe;color:#0f3460;font-size:.8rem;font-weight:600;padding:4px 14px;border-radius:20px;margin-bottom:1rem;border:1px solid #c5d8f7">📁 {cid} — {name}</div>'
        st.markdown(pill, unsafe_allow_html=True)
    else:
        st.info("💡 Open a case from the dashboard to let the agent read and act on it.")

    chat_col, help_col = st.columns([2, 1])

    with chat_col:
        if not history:
            st.markdown("""
            <div style="text-align:center;padding:2rem 1rem;background:#f8fafc;border-radius:16px;border:2px dashed #d0dce8;margin-bottom:1.5rem">
              <div style="font-size:2.5rem;margin-bottom:.75rem">🤖</div>
              <div style="font-size:1rem;font-weight:700;color:#0f3460;margin-bottom:.5rem">Hello! I'm your InvestiAI Assistant.</div>
              <div style="font-size:.88rem;color:#666;max-width:400px;margin:0 auto">
                Ask anything, or give me a command like <i>"retranslate the documents"</i>,
                <i>"change diagnosis to typhoid"</i>, or <i>"show me the case summary"</i>.
              </div>
            </div>""", unsafe_allow_html=True)
        else:
            for turn in history:
                if turn["role"] == "user":
                    st.markdown(f"""<div style="display:flex;justify-content:flex-end;margin-bottom:.75rem">
                      <div style="background:#0f3460;color:white;border-radius:16px 16px 4px 16px;padding:.65rem 1rem;max-width:82%;font-size:.88rem;line-height:1.55">{turn["content"]}</div>
                    </div>""", unsafe_allow_html=True)
                else:
                    st.markdown(f"""<div style="display:flex;gap:.75rem;margin-bottom:.75rem;align-items:flex-start">
                      <div style="background:#0f3460;color:white;border-radius:50%;width:32px;height:32px;display:flex;align-items:center;justify-content:center;font-size:.85rem;flex-shrink:0;margin-top:2px">🤖</div>
                      <div style="background:#f0f4f8;border-radius:4px 16px 16px 16px;padding:.65rem 1rem;max-width:88%;font-size:.88rem;line-height:1.6;border:1px solid #e0e8f0">{turn["content"].replace(chr(10),"<br>")}</div>
                    </div>""", unsafe_allow_html=True)

        if not history:
            st.markdown("**Try asking:**")
            chips = get_quick_questions(cid, 4)
            ccols = st.columns(2)
            for i,q in enumerate(chips):
                with ccols[i%2]:
                    if st.button(q, key=f"chip_{i}", use_container_width=True):
                        with st.spinner("Working…"):
                            resp, new_hist = ask_agent(q, history, cid, "")
                        st.session_state.agent_history = new_hist; st.rerun()

        st.markdown("<div style='height:.75rem'></div>", unsafe_allow_html=True)
        with st.form("agent_form", clear_on_submit=True):
            ic,bc = st.columns([6,1])
            with ic: user_input = st.text_input("","",placeholder="Ask a question or give a command…",label_visibility="collapsed",key="agent_text_input")
            with bc: sent = st.form_submit_button("Send",use_container_width=True,type="primary")

        if sent and user_input:
            with st.spinner("Thinking…"):
                resp, new_hist = ask_agent(user_input, history, cid, "")
            st.session_state.agent_history = new_hist; st.rerun()

        if history:
            if st.button("🗑️  Clear conversation", key="clear_hist"):
                st.session_state.agent_history = []; st.rerun()

    with help_col:
        st.markdown("""<div style="background:white;border-radius:12px;padding:1.25rem 1.5rem;
          box-shadow:0 2px 12px rgba(15,52,96,.08);border:1px solid #eef2f7">
          <div style="font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:#0f3460;margin-bottom:1rem;padding-bottom:.5rem;border-bottom:2px solid #e8f0fe">What I Can Do</div>
        """, unsafe_allow_html=True)
        for icon, title, items in [
            ("⚡","Take Actions",["Retranslate documents","Re-run OCR","Re-extract info","Update form fields","Re-assess fraud","Regenerate report","Rebuild timeline","Show case summary"]),
            ("📖","Read Your Case",["All uploaded documents","Extracted OCR text","Translated text","All form fields","Fraud scores"]),
            ("💡","Answer Questions",["InvestiAI features","Investigation tips","Fraud patterns","IRDAI regulations"]),
        ]:
            st.markdown(f"""<div style="margin-bottom:1rem">
              <div style="font-weight:700;font-size:.88rem;color:#1a1a2e;margin-bottom:.35rem">{icon} {title}</div>
              {"".join(f'<div style="font-size:.78rem;color:#666;padding:.15rem 0 .15rem 1rem">· {item}</div>' for item in items)}
            </div>""", unsafe_allow_html=True)
        if cid:
            st.markdown("""<div style="background:#e8f0fe;border-radius:8px;padding:.6rem .9rem;margin-top:.5rem;font-size:.8rem">
              <b>Command examples:</b><br>
              <i>"Retranslate documents"</i><br>
              <i>"Change diagnosis to typhoid"</i><br>
              <i>"Set claim amount to ₹50,000"</i><br>
              <i>"Re-run fraud assessment"</i>
            </div>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)


# ── ROUTER ────────────────────────────────────────────────────────────────────
def main():
    render_sidebar()
    page = st.session_state.get("page","dashboard")
    if   page == "dashboard":      page_dashboard()
    elif page == "new_case":       page_new_case()
    elif page == "case_workspace": page_case_workspace()
    elif page == "help_agent":     page_help_agent()
    elif page == "settings":       page_settings()
    else:                          page_dashboard()

if __name__ == "__main__":
    main()
