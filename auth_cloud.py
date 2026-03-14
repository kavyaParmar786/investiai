"""
auth_cloud.py
-------------
Production authentication for InvestiAI cloud deployment.

Supports:
  1. Email + Password  (local accounts, stored in SQLite)
  2. Google OAuth      (via streamlit-oauth or authlib)
  3. GitHub OAuth      (via streamlit-oauth or authlib)

All OAuth tokens are verified server-side — no client-side tricks.
Uses streamlit-oauth library for the OAuth flow.
"""

from __future__ import annotations
import hashlib, os, re, secrets, json
from datetime import datetime, timedelta

import streamlit as st

# ── streamlit-oauth (handles Google + GitHub flow) ───────────────────────────
try:
    from httpx_oauth.clients.google import GoogleOAuth2
    from httpx_oauth.clients.github import GitHubOAuth2
    OAUTH_AVAILABLE = True
except ImportError:
    OAUTH_AVAILABLE = False


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def _get_secret(key: str, default: str = "") -> str:
    """Read from st.secrets (cloud) or env var (local)."""
    try:
        return st.secrets.get(key, default) or os.environ.get(key, default)
    except Exception:
        return os.environ.get(key, default)

def _valid_email(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))

def _valid_password(pw: str) -> bool:
    return len(pw) >= 6


# ─────────────────────────────────────────────────────────────────────────────
# SESSION
# ─────────────────────────────────────────────────────────────────────────────

def init_session():
    defaults = {
        "logged_in":        False,
        "user":             None,
        "current_case_id":  None,
        "page":             "dashboard",
        "agent_history":    [],
        "auth_page":        "login",   # login | register | forgot
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def is_authenticated() -> bool:
    return bool(st.session_state.get("logged_in") and st.session_state.get("user"))


def get_current_user() -> dict | None:
    return st.session_state.get("user")


def _login_user(user: dict):
    st.session_state.logged_in = True
    st.session_state.user      = user
    st.session_state.page      = "dashboard"


def logout():
    for k in ["logged_in","user","current_case_id","agent_history"]:
        st.session_state[k] = None if k == "user" else ([] if k == "agent_history" else False)
    st.session_state.page = "dashboard"


# ─────────────────────────────────────────────────────────────────────────────
# DATABASE HELPERS  (imported lazily to avoid circular imports)
# ─────────────────────────────────────────────────────────────────────────────

def _db_get_user_by_email(email: str) -> dict | None:
    from database import get_conn
    conn = get_conn()
    row  = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    conn.close()
    return dict(row) if row else None


def _db_get_user_by_username(username: str) -> dict | None:
    from database import get_conn
    conn = get_conn()
    row  = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    return dict(row) if row else None


def _db_create_user(username: str, email: str, full_name: str,
                    password_hash: str = "", provider: str = "email",
                    avatar_url: str = "") -> dict | None:
    from database import get_conn
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO users (username,email,full_name,password,provider,avatar_url,role) VALUES (?,?,?,?,?,?,?)",
            (username, email, full_name, password_hash, provider, avatar_url, "investigator")
        )
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        return dict(row) if row else None
    except Exception:
        return None
    finally:
        conn.close()


def _db_upsert_oauth_user(email: str, full_name: str,
                           provider: str, avatar_url: str = "") -> dict:
    """Get or create a user from OAuth login."""
    existing = _db_get_user_by_email(email)
    if existing:
        return existing
    # Create new account — username = email prefix
    username = email.split("@")[0].lower().replace(".", "_")[:20]
    # Ensure unique username
    from database import get_conn
    conn = get_conn()
    i = 1
    base = username
    while conn.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
        username = f"{base}{i}"; i += 1
    conn.close()
    user = _db_create_user(username, email, full_name, "", provider, avatar_url)
    return user or {"username": username, "email": email, "full_name": full_name,
                    "role": "investigator", "provider": provider}


# ─────────────────────────────────────────────────────────────────────────────
# EMAIL / PASSWORD AUTH
# ─────────────────────────────────────────────────────────────────────────────

def login_email(email_or_username: str, password: str) -> tuple[bool, str]:
    """Returns (success, error_message)."""
    if not email_or_username or not password:
        return False, "Please enter your email/username and password."

    # Try email first, then username
    user = (_db_get_user_by_email(email_or_username)
            or _db_get_user_by_username(email_or_username))
    if not user:
        return False, "No account found with that email or username."
    if user.get("provider", "email") != "email":
        return False, f"This account uses {user['provider'].title()} sign-in. Use that button below."
    if user.get("password") != _hash(password):
        return False, "Incorrect password."

    _login_user(user)
    return True, ""


def register_email(full_name: str, email: str, username: str, password: str,
                   confirm: str) -> tuple[bool, str]:
    """Returns (success, error_message)."""
    if not all([full_name, email, username, password, confirm]):
        return False, "All fields are required."
    if not _valid_email(email):
        return False, "Please enter a valid email address."
    if not _valid_password(password):
        return False, "Password must be at least 6 characters."
    if password != confirm:
        return False, "Passwords do not match."
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        return False, "Username can only contain letters, numbers, and underscores."
    if _db_get_user_by_email(email):
        return False, "An account with this email already exists."
    if _db_get_user_by_username(username):
        return False, "That username is already taken. Try another."

    user = _db_create_user(username, email, full_name, _hash(password), "email")
    if not user:
        return False, "Registration failed. Please try again."

    _login_user(user)
    return True, ""


# ─────────────────────────────────────────────────────────────────────────────
# OAUTH  (Google + GitHub)
# ─────────────────────────────────────────────────────────────────────────────

def _get_oauth_redirect_uri() -> str:
    """Build the redirect URI for OAuth callbacks."""
    # On Streamlit Cloud the app URL comes from secrets or env
    base = _get_secret("APP_URL", "http://localhost:8501")
    return base.rstrip("/") + "/"


async def _google_get_user_info(code: str) -> dict | None:
    if not OAUTH_AVAILABLE:
        return None
    try:
        client = GoogleOAuth2(
            _get_secret("GOOGLE_CLIENT_ID"),
            _get_secret("GOOGLE_CLIENT_SECRET"),
        )
        token = await client.get_access_token(code, _get_oauth_redirect_uri())
        user_info = await client.get_id_email(token["access_token"])
        return {"email": user_info[1], "name": user_info[0] or user_info[1],
                "provider": "google", "avatar": ""}
    except Exception:
        return None


async def _github_get_user_info(code: str) -> dict | None:
    if not OAUTH_AVAILABLE:
        return None
    try:
        client = GitHubOAuth2(
            _get_secret("GITHUB_CLIENT_ID"),
            _get_secret("GITHUB_CLIENT_SECRET"),
        )
        token = await client.get_access_token(code, _get_oauth_redirect_uri())
        user_info = await client.get_profile(token["access_token"])
        email = user_info.get("email") or f"{user_info.get('login','')}@github.local"
        return {"email": email, "name": user_info.get("name") or user_info.get("login",""),
                "provider": "github", "avatar": user_info.get("avatar_url","")}
    except Exception:
        return None


def handle_oauth_callback() -> bool:
    """
    Check URL params for OAuth callback code.
    Returns True if a successful OAuth login was processed.
    """
    params = st.query_params
    code     = params.get("code", "")
    provider = params.get("state", "")   # we pass provider name in state param

    if not code:
        return False

    import asyncio

    user_info = None
    if provider == "google":
        user_info = asyncio.run(_google_get_user_info(code))
    elif provider == "github":
        user_info = asyncio.run(_github_get_user_info(code))

    if user_info:
        user = _db_upsert_oauth_user(
            user_info["email"], user_info["name"],
            user_info["provider"], user_info.get("avatar","")
        )
        if user:
            _login_user(user)
            # Clear OAuth params from URL
            st.query_params.clear()
            return True

    st.query_params.clear()
    return False


def get_google_auth_url() -> str:
    if not OAUTH_AVAILABLE:
        return ""
    try:
        import asyncio
        client = GoogleOAuth2(
            _get_secret("GOOGLE_CLIENT_ID"),
            _get_secret("GOOGLE_CLIENT_SECRET"),
        )
        url = asyncio.run(client.get_authorization_url(
            _get_oauth_redirect_uri(),
            scope=["openid", "email", "profile"],
            extras_params={"state": "google"},
        ))
        return url
    except Exception:
        return ""


def get_github_auth_url() -> str:
    if not OAUTH_AVAILABLE:
        return ""
    try:
        import asyncio
        client = GitHubOAuth2(
            _get_secret("GITHUB_CLIENT_ID"),
            _get_secret("GITHUB_CLIENT_SECRET"),
        )
        url = asyncio.run(client.get_authorization_url(
            _get_oauth_redirect_uri(),
            scope=["user:email"],
            extras_params={"state": "github"},
        ))
        return url
    except Exception:
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# LOGIN PAGE UI
# ─────────────────────────────────────────────────────────────────────────────

AUTH_CSS = """
<style>
.auth-wrap {
    max-width: 460px;
    margin: 40px auto;
    padding: 2.5rem 2rem;
    background: white;
    border-radius: 20px;
    box-shadow: 0 8px 48px rgba(15,52,96,0.13);
}
.auth-logo {
    text-align: center;
    font-size: 2.4rem;
    font-weight: 900;
    color: #0f3460;
    letter-spacing: -1px;
}
.auth-sub {
    text-align: center;
    color: #888;
    font-size: .88rem;
    margin-bottom: 1.75rem;
    margin-top: .2rem;
}
.divider {
    display: flex;
    align-items: center;
    gap: .75rem;
    color: #ccc;
    font-size: .82rem;
    margin: 1.25rem 0;
}
.divider::before, .divider::after {
    content: "";
    flex: 1;
    border-top: 1px solid #e8e8e8;
}
.oauth-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: .6rem;
    width: 100%;
    padding: .65rem 1rem;
    border: 1.5px solid #e0e0e0;
    border-radius: 10px;
    background: white;
    color: #333;
    font-size: .9rem;
    font-weight: 600;
    cursor: pointer;
    text-decoration: none;
    margin-bottom: .6rem;
    transition: all .2s;
}
.oauth-btn:hover { background: #f5f5f5; border-color: #bbb; }
.google-btn  { border-color: #ea4335; color: #ea4335; }
.github-btn  { border-color: #333;    color: #333;    }
</style>
"""


def show_auth_page():
    """Render the full login/register page."""
    st.markdown(AUTH_CSS, unsafe_allow_html=True)

    # Handle OAuth callback if present
    if handle_oauth_callback():
        st.rerun()

    _, col, _ = st.columns([1, 2, 1])
    with col:
        page = st.session_state.get("auth_page", "login")

        st.markdown("""
        <div class="auth-wrap">
          <div class="auth-logo">🔍 InvestiAI</div>
          <div class="auth-sub">Insurance Investigation Platform</div>
        """, unsafe_allow_html=True)

        if page == "login":
            _render_login()
        elif page == "register":
            _render_register()

        st.markdown("</div>", unsafe_allow_html=True)


def _render_oauth_buttons():
    """Render Google and GitHub sign-in buttons."""
    google_url = get_google_auth_url()
    github_url = get_github_auth_url()

    if google_url:
        st.markdown(f"""
        <a href="{google_url}" class="oauth-btn google-btn">
          <svg width="18" height="18" viewBox="0 0 48 48">
            <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
            <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
            <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
            <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
          </svg>
          Continue with Google
        </a>
        """, unsafe_allow_html=True)

    if github_url:
        st.markdown(f"""
        <a href="{github_url}" class="oauth-btn github-btn">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
          </svg>
          Continue with GitHub
        </a>
        """, unsafe_allow_html=True)

    if google_url or github_url:
        st.markdown('<div class="divider">or continue with email</div>', unsafe_allow_html=True)


def _render_login():
    _render_oauth_buttons()

    with st.form("login_form", clear_on_submit=False):
        email = st.text_input("Email or Username", placeholder="you@example.com")
        pw    = st.text_input("Password", type="password", placeholder="••••••••")
        submitted = st.form_submit_button("Sign In →", use_container_width=True, type="primary")

    if submitted:
        ok, err = login_email(email, pw)
        if ok:
            st.success("Welcome back!")
            st.rerun()
        else:
            st.error(err)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Create account", use_container_width=True):
            st.session_state.auth_page = "register"; st.rerun()
    with c2:
        st.markdown("""
        <div style="text-align:center;margin-top:.6rem;font-size:.8rem;color:#888">
          Demo: <b>admin</b> / <b>admin123</b>
        </div>""", unsafe_allow_html=True)


def _render_register():
    st.markdown("<div style='font-size:1.1rem;font-weight:700;color:#0f3460;margin-bottom:1rem'>Create your account</div>", unsafe_allow_html=True)

    _render_oauth_buttons()

    with st.form("register_form", clear_on_submit=False):
        full_name = st.text_input("Full Name *", placeholder="Ravi Sharma")
        email     = st.text_input("Email Address *", placeholder="ravi@company.com")
        username  = st.text_input("Username *", placeholder="ravi_sharma")
        pw        = st.text_input("Password *", type="password", placeholder="Min 6 characters")
        pw2       = st.text_input("Confirm Password *", type="password", placeholder="Repeat password")
        submitted = st.form_submit_button("Create Account →", use_container_width=True, type="primary")

    if submitted:
        ok, err = register_email(full_name, email, username, pw, pw2)
        if ok:
            st.success("Account created! Welcome to InvestiAI.")
            st.rerun()
        else:
            st.error(err)

    if st.button("← Back to Sign In", use_container_width=True):
        st.session_state.auth_page = "login"; st.rerun()


def require_auth():
    """Call at top of every page. Stops execution and shows login if not authenticated."""
    init_session()
    if not is_authenticated():
        show_auth_page()
        st.stop()
