#!/bin/bash
# ============================================================
#  InvestiAI - Pterodactyl Startup Script
#  Paste this as startup.sh in your Pterodactyl file manager
# ============================================================

echo ""
echo "╔══════════════════════════════════════╗"
echo "║   InvestiAI - Starting Up...         ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ── Step 1: Install system dependencies ──────────────────────
echo "[1/4] Installing system packages..."
apt-get update -qq 2>/dev/null
apt-get install -y -qq \
    tesseract-ocr \
    tesseract-ocr-hin \
    tesseract-ocr-guj \
    tesseract-ocr-eng \
    poppler-utils \
    libgl1-mesa-glx \
    libglib2.0-0 \
    gcc \
    g++ \
    2>/dev/null
echo "    System packages ready."

# ── Step 2: Install Python packages ──────────────────────────
echo "[2/4] Installing Python packages..."
pip install --upgrade pip --quiet
pip install \
    streamlit \
    requests \
    groq \
    httpx-oauth \
    pytesseract \
    Pillow \
    PyMuPDF \
    pdf2image \
    googletrans==4.0.0-rc1 \
    reportlab \
    python-docx \
    numpy \
    python-dateutil \
    easyocr \
    --quiet
echo "    Python packages ready."

# ── Step 3: Create directories ────────────────────────────────
echo "[3/4] Setting up directories..."
mkdir -p uploads exports templates .streamlit
echo "    Directories ready."

# ── Step 4: Create Streamlit config ──────────────────────────
echo "[4/4] Writing config..."
cat > .streamlit/config.toml << 'CONFIG'
[theme]
primaryColor = "#0f3460"
backgroundColor = "#f7f9fc"
secondaryBackgroundColor = "#ffffff"
textColor = "#1a1a2e"

[server]
port = 8501
address = "0.0.0.0"
headless = true
maxUploadSize = 50
enableXsrfProtection = true

[browser]
gatherUsageStats = false
CONFIG

# ── Write secrets from environment variables ──────────────────
cat > .streamlit/secrets.toml << SECRETS
GROQ_API_KEY = "${GROQ_API_KEY}"
APP_URL = "http://${SERVER_IP}:${SERVER_PORT}"
GOOGLE_CLIENT_ID = "${GOOGLE_CLIENT_ID}"
GOOGLE_CLIENT_SECRET = "${GOOGLE_CLIENT_SECRET}"
GITHUB_CLIENT_ID = "${GITHUB_CLIENT_ID}"
GITHUB_CLIENT_SECRET = "${GITHUB_CLIENT_SECRET}"
SECRETS

echo "    Config written."
echo ""
echo "✅ Setup complete! Launching InvestiAI..."
echo "   Access at: http://YOUR_SERVER_IP:${SERVER_PORT:-8501}"
echo ""

# ── Launch the app ────────────────────────────────────────────
exec streamlit run app.py \
    --server.port "${SERVER_PORT:-8501}" \
    --server.address "0.0.0.0" \
    --server.headless true \
    --browser.gatherUsageStats false
