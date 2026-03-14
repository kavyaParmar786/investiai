"""
utils.py
--------
Shared utility functions for InvestiAI.
"""

import os
import uuid
import hashlib
from datetime import datetime
from pathlib import Path

UPLOAD_DIR = Path("uploads")
EXPORT_DIR = Path("exports")


def ensure_dirs():
    """Create required directories if missing."""
    UPLOAD_DIR.mkdir(exist_ok=True)
    EXPORT_DIR.mkdir(exist_ok=True)


def generate_case_id() -> str:
    """Generate a unique case ID like INV-2025-0001."""
    date_part = datetime.now().strftime("%Y")
    random_part = str(uuid.uuid4())[:6].upper()
    return f"INV-{date_part}-{random_part}"


def save_uploaded_file(uploaded_file, case_id: str) -> dict:
    """
    Save a Streamlit UploadedFile to disk.

    Returns:
        {"filename": str, "filepath": str, "size": int, "success": bool}
    """
    ensure_dirs()
    case_dir = UPLOAD_DIR / case_id
    case_dir.mkdir(exist_ok=True)

    # Sanitize filename
    safe_name = sanitize_filename(uploaded_file.name)
    filepath = case_dir / safe_name

    # Handle duplicate filenames
    counter = 1
    while filepath.exists():
        stem = Path(safe_name).stem
        suffix = Path(safe_name).suffix
        filepath = case_dir / f"{stem}_{counter}{suffix}"
        counter += 1

    try:
        with open(filepath, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return {
            "filename": filepath.name,
            "filepath": str(filepath),
            "size": filepath.stat().st_size,
            "success": True,
        }
    except Exception as e:
        return {"filename": "", "filepath": "", "size": 0, "success": False, "error": str(e)}


def sanitize_filename(filename: str) -> str:
    """Remove unsafe characters from filename."""
    import re
    # Keep alphanumeric, dots, hyphens, underscores, spaces
    safe = re.sub(r"[^\w\s\.\-]", "", filename)
    safe = safe.strip().replace(" ", "_")
    return safe or "document"


def format_file_size(size_bytes: int) -> str:
    """Human-readable file size."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024**2):.1f} MB"


def format_date(date_str: str) -> str:
    """Attempt to parse and nicely format a date string."""
    if not date_str:
        return ""
    for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%dT%H:%M:%S"]:
        try:
            return datetime.strptime(date_str, fmt).strftime("%d %b %Y")
        except ValueError:
            pass
    return date_str


def get_risk_color(risk_level: str) -> str:
    """Return a hex color for the risk level."""
    mapping = {
        "Low Risk":    "#27ae60",
        "Medium Risk": "#f39c12",
        "High Risk":   "#e74c3c",
    }
    return mapping.get(risk_level, "#95a5a6")


def get_risk_emoji(risk_level: str) -> str:
    mapping = {
        "Low Risk":    "🟢",
        "Medium Risk": "🟡",
        "High Risk":   "🔴",
    }
    return mapping.get(risk_level, "⚪")


def get_status_color(status: str) -> str:
    mapping = {
        "Open":        "#3498db",
        "In Progress": "#f39c12",
        "Closed":      "#27ae60",
        "Escalated":   "#e74c3c",
    }
    return mapping.get(status, "#95a5a6")


def truncate_text(text: str, max_length: int = 200) -> str:
    if not text:
        return ""
    return text[:max_length] + "..." if len(text) > max_length else text


def get_export_path(case_id: str, fmt: str) -> str:
    """Generate export file path."""
    ensure_dirs()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{case_id}_{timestamp}.{fmt}"
    return str(EXPORT_DIR / filename)


def get_timeline_category_emoji(category: str) -> str:
    mapping = {
        "incident":     "⚡",
        "medical":      "🏥",
        "claim":        "📋",
        "investigation": "🔍",
        "other":        "📌",
    }
    return mapping.get(category.lower(), "📌")


# CSS for the app
APP_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

* { font-family: 'Inter', sans-serif; }
code, pre { font-family: 'JetBrains Mono', monospace !important; }

/* Remove default Streamlit padding */
.block-container { padding-top: 1.5rem !important; padding-bottom: 2rem !important; }

/* Hide Streamlit default elements */
#MainMenu, footer, header { visibility: hidden; }

/* Custom scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #f1f1f1; }
::-webkit-scrollbar-thumb { background: #0f3460; border-radius: 3px; }

/* Metric cards */
.metric-card {
    background: white;
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    box-shadow: 0 2px 12px rgba(15,52,96,0.08);
    border-left: 4px solid #0f3460;
    margin-bottom: 1rem;
}
.metric-value {
    font-size: 2rem;
    font-weight: 800;
    color: #0f3460;
    line-height: 1;
}
.metric-label {
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #888;
    margin-top: 0.3rem;
}

/* Section cards */
.section-card {
    background: white;
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: 0 2px 16px rgba(15,52,96,0.08);
    margin-bottom: 1.5rem;
    border: 1px solid #eef2f7;
}
.section-header {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #0f3460;
    padding-bottom: 0.75rem;
    border-bottom: 2px solid #e8f0fe;
    margin-bottom: 1rem;
}

/* Risk badge */
.risk-badge {
    display: inline-block;
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.05em;
}

/* Timeline item */
.timeline-item {
    display: flex;
    gap: 1rem;
    padding: 0.75rem 0;
    border-bottom: 1px solid #f0f4f8;
}
.timeline-date {
    min-width: 130px;
    font-size: 0.82rem;
    color: #0f3460;
    font-weight: 600;
}
.timeline-event {
    font-size: 0.88rem;
    color: #333;
}

/* Status badge */
.status-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
    color: white;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #0f3460 !important;
}
section[data-testid="stSidebar"] * {
    color: white !important;
}
section[data-testid="stSidebar"] .stButton button {
    background: rgba(255,255,255,0.1) !important;
    border: 1px solid rgba(255,255,255,0.2) !important;
    color: white !important;
    width: 100%;
    text-align: left;
    border-radius: 8px;
    padding: 0.5rem 1rem;
}
section[data-testid="stSidebar"] .stButton button:hover {
    background: rgba(255,255,255,0.2) !important;
}

/* Main buttons */
.stButton > button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    letter-spacing: 0.02em !important;
    transition: all 0.2s ease !important;
}
.stButton > button[kind="primary"] {
    background: #0f3460 !important;
    border: none !important;
}
.stButton > button[kind="primary"]:hover {
    background: #16213e !important;
    box-shadow: 0 4px 12px rgba(15,52,96,0.25) !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.5rem;
    background: #f7f9fc;
    padding: 0.4rem;
    border-radius: 10px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
}

/* Text areas and inputs */
.stTextArea textarea, .stTextInput input {
    border-radius: 8px !important;
    border-color: #d0dce8 !important;
    font-size: 0.9rem !important;
}
.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: #0f3460 !important;
    box-shadow: 0 0 0 2px rgba(15,52,96,0.15) !important;
}

/* Success/info boxes */
.stSuccess { border-radius: 8px !important; }
.stInfo { border-radius: 8px !important; }
.stWarning { border-radius: 8px !important; }
.stError { border-radius: 8px !important; }

/* Dataframe */
.dataframe { font-size: 0.85rem !important; }
</style>
"""
