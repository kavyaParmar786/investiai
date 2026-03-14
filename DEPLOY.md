# 🔍 InvestiAI — Cloud Deployment Guide

Deploy InvestiAI as a **real public website** — free hosting, free AI, free login.

---

## What you get

| Feature | Details |
|---------|---------|
| 🌐 Public URL | `https://your-app.streamlit.app` |
| 🔐 Login | Email/password + Google + GitHub |
| 🤖 Free AI | Groq API (14,400 requests/day free) |
| 💾 Hosting | Streamlit Community Cloud (free forever) |
| 👥 Users | Anyone can register and use it |

---

## Step-by-step deployment

### Step 1 — Create a GitHub account (free)
Go to **https://github.com** and create a free account if you don't have one.

---

### Step 2 — Upload the code to GitHub

1. Go to https://github.com/new and create a new repository
   - Name it: `investiai`
   - Set to **Private** (recommended) or Public
   - Click **Create repository**

2. Upload all files from this folder to the repository:
   - Click **uploading an existing file**
   - Drag and drop ALL files from this folder (except `secrets.toml.template`)
   - Click **Commit changes**

---

### Step 3 — Get your FREE Groq API key

1. Go to **https://console.groq.com**
2. Click **Sign Up** (use Google or email — it's free)
3. Click **API Keys** → **Create API Key**
4. Copy the key (starts with `gsk_...`)
5. Save it — you'll need it in the next step

**Free tier:** 14,400 requests/day — enough for a full team of investigators.

---

### Step 4 — Deploy on Streamlit Community Cloud (free)

1. Go to **https://streamlit.io/cloud** and sign in with GitHub
2. Click **New app**
3. Select your `investiai` repository
4. Set **Main file path** to `app.py`
5. Click **Advanced settings** → **Secrets**
6. Paste the following (replace the values with your actual keys):

```toml
GROQ_API_KEY = "gsk_your_groq_key_here"
APP_URL = "https://your-app-name.streamlit.app"
```

7. Click **Deploy** — your app will be live in ~2 minutes!

Your URL will be: `https://your-app-name.streamlit.app`

---

### Step 5 (Optional) — Add Google Sign-In

1. Go to **https://console.cloud.google.com**
2. Create a new project → **APIs & Services** → **Credentials**
3. Click **Create Credentials** → **OAuth 2.0 Client ID**
4. Application type: **Web application**
5. Add Authorized redirect URI: `https://your-app-name.streamlit.app/`
6. Copy Client ID and Client Secret
7. Add to your Streamlit secrets:

```toml
GOOGLE_CLIENT_ID     = "your-client-id.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "your-client-secret"
```

---

### Step 6 (Optional) — Add GitHub Sign-In

1. Go to **https://github.com/settings/developers**
2. Click **New OAuth App**
3. Homepage URL: `https://your-app-name.streamlit.app`
4. Callback URL: `https://your-app-name.streamlit.app/`
5. Click **Register application**
6. Copy Client ID and generate Client Secret
7. Add to your Streamlit secrets:

```toml
GITHUB_CLIENT_ID     = "your-github-client-id"
GITHUB_CLIENT_SECRET = "your-github-client-secret"
```

---

## Default login credentials

Once deployed, anyone can register. These demo accounts are pre-created:

| Username | Password | Role |
|----------|----------|------|
| `admin` | `admin123` | Admin |
| `investigator1` | `inv123` | Investigator |

**Change these immediately** after first login.

---

## File structure

```
investiai_cloud/
├── app.py                  ← Main application
├── auth_cloud.py           ← Login / Register / OAuth
├── groq_ai.py              ← Free AI engine (Groq)
├── ai_agent.py             ← Help Agent with actions
├── ai_extractor.py         ← Document field extraction
├── fraud_detector.py       ← Fraud risk scoring
├── report_generator.py     ← Report + PDF generation
├── timeline_generator.py   ← Event timeline
├── database.py             ← SQLite database
├── ocr_engine.py           ← Tesseract OCR
├── handwriting_ocr.py      ← EasyOCR handwriting
├── translator.py           ← Google Translate (free)
├── utils.py                ← Shared utilities
├── requirements.txt        ← Python dependencies
├── .gitignore              ← Excludes secrets from Git
└── .streamlit/
    ├── config.toml         ← UI theme settings
    └── secrets.toml.template ← Copy → secrets.toml, fill in keys
```

---

## Important notes

### Database
Streamlit Community Cloud resets files on redeploy. For a **production app** with permanent data:
- Use **Supabase** (free PostgreSQL) or **PlanetScale** (free MySQL)
- Or upgrade to a paid VPS and run there

For testing and small teams, the SQLite database works fine.

### File uploads
Uploaded documents are stored on the server's disk. On Streamlit Cloud, these reset on redeploy. For permanent file storage, use:
- **Cloudflare R2** (free 10 GB)
- **Backblaze B2** (free 10 GB)
- **AWS S3** (free tier)

### OCR on the server
Tesseract needs to be installed on the server. On Streamlit Cloud, add a `packages.txt` file:

```
tesseract-ocr
tesseract-ocr-hin
tesseract-ocr-guj
poppler-utils
```

This makes Streamlit Cloud install system packages automatically.

---

## Updating the app

To update the live site:
1. Edit files locally
2. Upload changed files to GitHub
3. Streamlit Cloud redeploys automatically

---

## Cost summary

| Service | Cost |
|---------|------|
| Streamlit Cloud hosting | **Free** |
| Groq AI (14,400 req/day) | **Free** |
| Google OAuth | **Free** |
| GitHub OAuth | **Free** |
| GitHub repository | **Free** |
| **Total** | **₹0 / month** |
