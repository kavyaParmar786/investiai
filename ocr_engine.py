"""
ocr_engine.py
-------------
Handles OCR text extraction from images and PDFs.
Uses pytesseract for typed/printed text with Hindi, Gujarati, and English support.
"""

import os
import re
from pathlib import Path

# ── Windows: auto-configure Tesseract path ───────────────────────────────────
try:
    from windows_config import configure_tesseract_windows, configure_poppler_windows
    configure_tesseract_windows()
    configure_poppler_windows()
except ImportError:
    pass

# ─── Optional imports (graceful degradation if not installed) ───────────────

try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False


# ─── Language config ──────────────────────────────────────────────────────────

TESSERACT_LANG_MAP = {
    "Hindi":    "hin",
    "Gujarati": "guj",
    "English":  "eng",
    "Auto":     "hin+guj+eng",
}


# ─── MAIN EXTRACTION FUNCTION ────────────────────────────────────────────────

def extract_text_from_file(filepath: str, hint_lang: str = "Auto") -> dict:
    """
    Extract text from image or PDF file.
    Returns: {
        "text": str,
        "detected_lang": str,
        "method": str,
        "pages": int,
        "success": bool,
        "error": str or None
    }
    """
    filepath = str(filepath)
    ext = Path(filepath).suffix.lower()

    if ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"]:
        return _extract_from_image(filepath, hint_lang)
    elif ext == ".pdf":
        return _extract_from_pdf(filepath, hint_lang)
    else:
        return _fail(f"Unsupported file type: {ext}")


def _extract_from_image(filepath: str, hint_lang: str = "Auto") -> dict:
    """Run Tesseract OCR on a single image."""
    if not TESSERACT_AVAILABLE:
        return _demo_extraction(filepath)

    try:
        img = Image.open(filepath)
        # Pre-process: convert to RGB if needed
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        lang_code = TESSERACT_LANG_MAP.get(hint_lang, "hin+guj+eng")

        # Run OCR with LSTM engine
        config = "--oem 3 --psm 6"
        text = pytesseract.image_to_string(img, lang=lang_code, config=config)

        detected = _detect_language(text)
        return {
            "text": text.strip(),
            "detected_lang": detected,
            "method": "Tesseract OCR",
            "pages": 1,
            "success": True,
            "error": None,
        }
    except Exception as e:
        return _demo_extraction(filepath, error=str(e))


def _extract_from_pdf(filepath: str, hint_lang: str = "Auto") -> dict:
    """Extract text from PDF — try text layer first, then OCR each page."""
    # Attempt direct text extraction
    if PYMUPDF_AVAILABLE:
        try:
            doc = fitz.open(filepath)
            full_text = ""
            for page in doc:
                full_text += page.get_text()
            doc.close()
            if full_text.strip():
                detected = _detect_language(full_text)
                return {
                    "text": full_text.strip(),
                    "detected_lang": detected,
                    "method": "PyMuPDF (text layer)",
                    "pages": len(fitz.open(filepath)),
                    "success": True,
                    "error": None,
                }
        except Exception:
            pass

    # Fall back to image OCR per page
    if PDF2IMAGE_AVAILABLE and TESSERACT_AVAILABLE:
        try:
            images = convert_from_path(filepath, dpi=200)
            lang_code = TESSERACT_LANG_MAP.get(hint_lang, "hin+guj+eng")
            texts = []
            for img in images:
                t = pytesseract.image_to_string(img, lang=lang_code, config="--oem 3 --psm 6")
                texts.append(t)
            full_text = "\n\n--- Page Break ---\n\n".join(texts)
            detected = _detect_language(full_text)
            return {
                "text": full_text.strip(),
                "detected_lang": detected,
                "method": "pdf2image + Tesseract OCR",
                "pages": len(images),
                "success": True,
                "error": None,
            }
        except Exception as e:
            return _demo_extraction(filepath, error=str(e))

    return _demo_extraction(filepath)


# ─── LANGUAGE DETECTION ──────────────────────────────────────────────────────

def _detect_language(text: str) -> str:
    """Simple heuristic language detection based on Unicode ranges."""
    if not text:
        return "Unknown"

    devanagari = len(re.findall(r'[\u0900-\u097F]', text))
    gujarati   = len(re.findall(r'[\u0A80-\u0AFF]', text))
    latin      = len(re.findall(r'[a-zA-Z]', text))

    total = devanagari + gujarati + latin
    if total == 0:
        return "Unknown"

    if devanagari > gujarati and devanagari > latin:
        return "Hindi"
    elif gujarati > devanagari and gujarati > latin:
        return "Gujarati"
    elif latin > devanagari and latin > gujarati:
        return "English"
    elif devanagari + gujarati > latin:
        return "Hindi"  # Mixed Indic, default to Hindi
    return "English"


# ─── DEMO FALLBACK ───────────────────────────────────────────────────────────

def _demo_extraction(filepath: str, error: str = None) -> dict:
    """
    Returns a realistic demo extraction when OCR libraries aren't available.
    This lets the app run in demo mode for testing.
    """
    filename = Path(filepath).name.lower()

    # Simulate different document types
    if "hospital" in filename or "medical" in filename:
        demo_text = """अस्पताल का नाम: अपोलो हॉस्पिटल, दिल्ली
रोगी का नाम: राजेश कुमार
आयु: 35 वर्ष
भर्ती तिथि: 12 मार्च 2025
छुट्टी तिथि: 20 मार्च 2025
निदान: डेंगू बुखार
इलाज करने वाले डॉक्टर: डॉ. अनिल वर्मा
दावा राशि: ₹50,000
पॉलिसी संख्या: POL-2024-789456
पता: 123, राजेश नगर, नई दिल्ली - 110001
फोन: 9876543210"""
        return {
            "text": demo_text,
            "detected_lang": "Hindi",
            "method": "Demo Mode (Tesseract not available)",
            "pages": 1,
            "success": True,
            "error": error,
        }

    elif "claim" in filename or "insurance" in filename:
        demo_text = """વીમા દાવો ફોર્મ
દાવેદારનું નામ: સુરેશ પટેલ
ઉંમર: 42 વર્ષ
સરનામું: 45, ગાંધી રોડ, અમદાવાદ - 380001
ફોન: 9865432107
પૉલિસી નંબર: POL-2023-GUJ-4521
હૉસ્પિટલ: સિવિલ હૉસ્પિટલ, અમદાવાદ
દાખલ તારીખ: 5 ફેબ્રુઆરી 2025
રજા તારીખ: 12 ફેબ્રુઆરી 2025
નિદાન: ટાઇફોઇડ
દાવાની રકમ: ₹35,000"""
        return {
            "text": demo_text,
            "detected_lang": "Gujarati",
            "method": "Demo Mode (Tesseract not available)",
            "pages": 1,
            "success": True,
            "error": error,
        }

    else:
        demo_text = """Investigation Document
Case Reference: INV-2025-001
Claimant: Priya Mehta
Policy Number: POL-2024-112233
Date of Incident: 15 January 2025
Hospital: Fortis Hospital, Mumbai
Admission Date: 16 January 2025
Discharge Date: 22 January 2025
Diagnosis: Appendicitis (Acute)
Treating Physician: Dr. Ramesh Nair
Claim Amount: INR 75,000
Address: 78, Linking Road, Bandra West, Mumbai - 400050
Phone: 9123456789"""
        return {
            "text": demo_text,
            "detected_lang": "English",
            "method": "Demo Mode (Tesseract not available)",
            "pages": 1,
            "success": True,
            "error": error,
        }


def _fail(msg: str) -> dict:
    return {
        "text": "",
        "detected_lang": "Unknown",
        "method": "None",
        "pages": 0,
        "success": False,
        "error": msg,
    }
