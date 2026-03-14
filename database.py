"""
database.py
-----------
SQLite database setup and all CRUD operations for InvestiAI.
Handles: cases, documents, extracted_text, translations, form_data, reports, fraud_scores, users
"""

import sqlite3
import hashlib
import os
import json
from datetime import datetime

DB_PATH = "investiai.db"


def get_conn():
    """Return a thread-safe SQLite connection with row_factory enabled."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


# ─────────────────────────────────────────────
# SCHEMA SETUP
# ─────────────────────────────────────────────

def init_db():
    """Create all tables if they don't exist. Safe to call on every startup."""
    conn = get_conn()
    c = conn.cursor()

    # Users
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT UNIQUE NOT NULL,
            email       TEXT UNIQUE,
            password    TEXT DEFAULT '',
            full_name   TEXT,
            role        TEXT DEFAULT 'investigator',
            provider    TEXT DEFAULT 'email',
            avatar_url  TEXT DEFAULT '',
            created_at  TEXT DEFAULT (datetime('now'))
        )
    """)
    # Migrate existing installs
    for col, coltype in [("email","TEXT"),("provider","TEXT DEFAULT ''email''"),
                         ("avatar_url","TEXT DEFAULT ''")]:
        try:
            c.execute(f"ALTER TABLE users ADD COLUMN {col} {coltype}")
        except Exception:
            pass

    # Cases
    c.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id         TEXT UNIQUE NOT NULL,
            claimant_name   TEXT,
            policy_number   TEXT,
            status          TEXT DEFAULT 'Open',
            assigned_to     TEXT,
            notes           TEXT,
            created_at      TEXT DEFAULT (datetime('now')),
            updated_at      TEXT DEFAULT (datetime('now'))
        )
    """)

    # Documents
    c.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id         TEXT NOT NULL,
            filename        TEXT NOT NULL,
            filepath        TEXT NOT NULL,
            doc_type        TEXT,
            uploaded_at     TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (case_id) REFERENCES cases(case_id)
        )
    """)

    # Extracted text
    c.execute("""
        CREATE TABLE IF NOT EXISTS extracted_text (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id          INTEGER NOT NULL,
            case_id         TEXT NOT NULL,
            raw_text        TEXT,
            detected_lang   TEXT,
            is_handwritten  INTEGER DEFAULT 0,
            extracted_at    TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (doc_id) REFERENCES documents(id)
        )
    """)

    # Translations
    c.execute("""
        CREATE TABLE IF NOT EXISTS translations (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            extracted_id    INTEGER NOT NULL,
            case_id         TEXT NOT NULL,
            original_text   TEXT,
            translated_text TEXT,
            source_lang     TEXT,
            target_lang     TEXT DEFAULT 'en',
            translated_at   TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (extracted_id) REFERENCES extracted_text(id)
        )
    """)

    # Form data (auto-extracted + manually edited)
    c.execute("""
        CREATE TABLE IF NOT EXISTS form_data (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id             TEXT UNIQUE NOT NULL,
            claimant_name       TEXT,
            policy_number       TEXT,
            age                 TEXT,
            address             TEXT,
            phone               TEXT,
            hospital_name       TEXT,
            hospital_address    TEXT,
            claim_amount        TEXT,
            incident_date       TEXT,
            admission_date      TEXT,
            discharge_date      TEXT,
            diagnosis           TEXT,
            doctor_name         TEXT,
            investigator_notes  TEXT,
            suspicious_indicators TEXT,
            treatment_duration  TEXT,
            insurance_company   TEXT,
            nominee_name        TEXT,
            relationship        TEXT,
            raw_json            TEXT,
            updated_at          TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (case_id) REFERENCES cases(case_id)
        )
    """)

    # Migrate: add columns to existing table if upgrading from older schema
    _migrate_form_data(c)

    # Reports
    c.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id         TEXT NOT NULL,
            report_text     TEXT,
            key_points      TEXT,
            timeline_json   TEXT,
            generated_at    TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (case_id) REFERENCES cases(case_id)
        )
    """)

    # Fraud scores
    c.execute("""
        CREATE TABLE IF NOT EXISTS fraud_scores (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id         TEXT NOT NULL,
            score           INTEGER,
            risk_level      TEXT,
            explanation     TEXT,
            indicators      TEXT,
            scored_at       TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (case_id) REFERENCES cases(case_id)
        )
    """)

    conn.commit()

    # Seed default admin user
    _seed_default_user(c, conn)
    conn.close()


def _migrate_form_data(c):
    """Add any missing columns to form_data for backward compatibility."""
    extra_cols = [
        ("treatment_duration", "TEXT"),
        ("insurance_company",  "TEXT"),
        ("nominee_name",       "TEXT"),
        ("relationship",       "TEXT"),
    ]
    for col, col_type in extra_cols:
        try:
            c.execute(f"ALTER TABLE form_data ADD COLUMN {col} {col_type}")
        except Exception:
            pass  # Column already exists


def _seed_default_user(c, conn):
    """Insert default admin if no users exist."""
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        pw = _hash_password("admin123")
        c.execute(
            "INSERT INTO users (username, email, password, full_name, role, provider) VALUES (?,?,?,?,?,?)",
            ("admin", "admin@investiai.com", pw, "Administrator", "admin", "email")
        )
        c.execute(
            "INSERT INTO users (username, email, password, full_name, role, provider) VALUES (?,?,?,?,?,?)",
            ("investigator1", "inv1@investiai.com", _hash_password("inv123"), "Ravi Sharma", "investigator", "email")
        )
        conn.commit()


def _hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


# ─────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────

def verify_user(username: str, password: str):
    """Return user row if credentials valid, else None."""
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()
    if row and row["password"] == _hash_password(password):
        return dict(row)
    return None


def get_all_users():
    conn = get_conn()
    rows = conn.execute("SELECT id, username, full_name, role, created_at FROM users").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────
# CASES
# ─────────────────────────────────────────────

def create_case(case_id, claimant_name, policy_number, assigned_to="", notes=""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO cases (case_id, claimant_name, policy_number, assigned_to, notes) VALUES (?,?,?,?,?)",
        (case_id, claimant_name, policy_number, assigned_to, notes)
    )
    conn.commit()
    conn.close()


def get_all_cases():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM cases ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_case(case_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM cases WHERE case_id=?", (case_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_case(case_id, **kwargs):
    kwargs["updated_at"] = datetime.now().isoformat()
    fields = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [case_id]
    conn = get_conn()
    conn.execute(f"UPDATE cases SET {fields} WHERE case_id=?", vals)
    conn.commit()
    conn.close()


def delete_case(case_id):
    conn = get_conn()
    conn.execute("DELETE FROM cases WHERE case_id=?", (case_id,))
    conn.execute("DELETE FROM documents WHERE case_id=?", (case_id,))
    conn.execute("DELETE FROM extracted_text WHERE case_id=?", (case_id,))
    conn.execute("DELETE FROM translations WHERE case_id=?", (case_id,))
    conn.execute("DELETE FROM form_data WHERE case_id=?", (case_id,))
    conn.execute("DELETE FROM reports WHERE case_id=?", (case_id,))
    conn.execute("DELETE FROM fraud_scores WHERE case_id=?", (case_id,))
    conn.commit()
    conn.close()


def search_cases(query: str):
    conn = get_conn()
    like = f"%{query}%"
    rows = conn.execute(
        "SELECT * FROM cases WHERE case_id LIKE ? OR claimant_name LIKE ? OR policy_number LIKE ? ORDER BY created_at DESC",
        (like, like, like)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────
# DOCUMENTS
# ─────────────────────────────────────────────

def save_document(case_id, filename, filepath, doc_type=""):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO documents (case_id, filename, filepath, doc_type) VALUES (?,?,?,?)",
        (case_id, filename, filepath, doc_type)
    )
    doc_id = c.lastrowid
    conn.commit()
    conn.close()
    return doc_id


def get_documents(case_id):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM documents WHERE case_id=? ORDER BY uploaded_at", (case_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────
# EXTRACTED TEXT
# ─────────────────────────────────────────────

def save_extracted_text(doc_id, case_id, raw_text, detected_lang="en", is_handwritten=False):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO extracted_text (doc_id, case_id, raw_text, detected_lang, is_handwritten) VALUES (?,?,?,?,?)",
        (doc_id, case_id, raw_text, detected_lang, int(is_handwritten))
    )
    ext_id = c.lastrowid
    conn.commit()
    conn.close()
    return ext_id


def get_extracted_texts(case_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT et.*, d.filename FROM extracted_text et JOIN documents d ON et.doc_id=d.id WHERE et.case_id=? ORDER BY et.extracted_at",
        (case_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────
# TRANSLATIONS
# ─────────────────────────────────────────────

def save_translation(extracted_id, case_id, original_text, translated_text, source_lang):
    conn = get_conn()
    conn.execute(
        "INSERT INTO translations (extracted_id, case_id, original_text, translated_text, source_lang) VALUES (?,?,?,?,?)",
        (extracted_id, case_id, original_text, translated_text, source_lang)
    )
    conn.commit()
    conn.close()


def get_translations(case_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT t.*, d.filename FROM translations t JOIN extracted_text et ON t.extracted_id=et.id JOIN documents d ON et.doc_id=d.id WHERE t.case_id=? ORDER BY t.translated_at",
        (case_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────
# FORM DATA
# ─────────────────────────────────────────────

def save_form_data(case_id, data: dict):
    conn = get_conn()
    existing = conn.execute("SELECT id FROM form_data WHERE case_id=?", (case_id,)).fetchone()
    data["updated_at"] = datetime.now().isoformat()
    data["case_id"] = case_id
    if existing:
        fields = ", ".join(f"{k}=?" for k in data if k != "case_id")
        vals = [v for k, v in data.items() if k != "case_id"] + [case_id]
        conn.execute(f"UPDATE form_data SET {fields} WHERE case_id=?", vals)
    else:
        cols = ", ".join(data.keys())
        placeholders = ", ".join("?" for _ in data)
        conn.execute(f"INSERT INTO form_data ({cols}) VALUES ({placeholders})", list(data.values()))
    conn.commit()
    conn.close()


def get_form_data(case_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM form_data WHERE case_id=?", (case_id,)).fetchone()
    conn.close()
    return dict(row) if row else {}


# ─────────────────────────────────────────────
# REPORTS
# ─────────────────────────────────────────────

def save_report(case_id, report_text, key_points="", timeline_json=""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO reports (case_id, report_text, key_points, timeline_json) VALUES (?,?,?,?)",
        (case_id, report_text, key_points, timeline_json)
    )
    conn.commit()
    conn.close()


def get_latest_report(case_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM reports WHERE case_id=? ORDER BY generated_at DESC LIMIT 1", (case_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else {}


# ─────────────────────────────────────────────
# FRAUD SCORES
# ─────────────────────────────────────────────

def save_fraud_score(case_id, score, risk_level, explanation, indicators):
    conn = get_conn()
    conn.execute(
        "INSERT INTO fraud_scores (case_id, score, risk_level, explanation, indicators) VALUES (?,?,?,?,?)",
        (case_id, score, risk_level, explanation, indicators)
    )
    conn.commit()
    conn.close()


def get_latest_fraud_score(case_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM fraud_scores WHERE case_id=? ORDER BY scored_at DESC LIMIT 1", (case_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else {}


def get_case_stats():
    """Summary stats for the dashboard."""
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
    open_c = conn.execute("SELECT COUNT(*) FROM cases WHERE status='Open'").fetchone()[0]
    closed_c = conn.execute("SELECT COUNT(*) FROM cases WHERE status='Closed'").fetchone()[0]
    high_risk = conn.execute("SELECT COUNT(*) FROM fraud_scores WHERE risk_level='High Risk'").fetchone()[0]
    conn.close()
    return {"total": total, "open": open_c, "closed": closed_c, "high_risk": high_risk}
