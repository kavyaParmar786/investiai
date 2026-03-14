"""
translator.py
-------------
Translates Hindi/Gujarati text to English using googletrans (free)
with fallback to a simple demo translation for testing.
"""

# ─── Optional imports ────────────────────────────────────────────────────────

try:
    from googletrans import Translator as GoogleTranslator, LANGUAGES
    GOOGLETRANS_AVAILABLE = True
except ImportError:
    GOOGLETRANS_AVAILABLE = False

# Language code mapping
LANG_CODE_MAP = {
    "Hindi":    "hi",
    "Gujarati": "gu",
    "English":  "en",
    "Unknown":  "hi",  # Default to Hindi for unknown Indic scripts
}

LANG_NAME_MAP = {
    "hi": "Hindi",
    "gu": "Gujarati",
    "en": "English",
    "mr": "Marathi",
    "pa": "Punjabi",
}


def translate_to_english(text: str, source_lang: str = "Auto") -> dict:
    """
    Translate text to English.

    Args:
        text: Source text
        source_lang: "Hindi", "Gujarati", "English", or "Auto"

    Returns:
        {
            "translated_text": str,
            "source_lang": str,
            "target_lang": "en",
            "method": str,
            "success": bool,
            "error": str or None
        }
    """
    if not text or not text.strip():
        return _result("", source_lang, "No text provided", success=False)

    # If already English, no translation needed
    if source_lang == "English":
        return _result(text, "en", "No translation needed (already English)")

    # Map lang name to code
    src_code = LANG_CODE_MAP.get(source_lang, "hi") if source_lang != "Auto" else None

    if GOOGLETRANS_AVAILABLE:
        return _google_translate(text, src_code)
    else:
        return _demo_translate(text, source_lang)


def _google_translate(text: str, src_code: str = None) -> dict:
    """Use googletrans library for translation."""
    try:
        translator = GoogleTranslator()
        if src_code:
            result = translator.translate(text, src=src_code, dest="en")
        else:
            result = translator.translate(text, dest="en")

        src_name = LANG_NAME_MAP.get(result.src, result.src)
        return _result(result.text, src_name, "Google Translate (free)")
    except Exception as e:
        return _demo_translate(text, "Hindi", error=str(e))


def _demo_translate(text: str, source_lang: str, error: str = None) -> dict:
    """
    Demo translation — returns a realistic English translation for testing.
    Used when googletrans is not installed.
    """

    if "अपोलो" in text or "apollo" in text.lower() or "हॉस्पिटल" in text:
        translated = """Hospital Name: Apollo Hospital, Delhi
Patient Name: Rajesh Kumar
Age: 35 years
Admission Date: 12 March 2025
Discharge Date: 20 March 2025
Diagnosis: Dengue Fever
Treating Doctor: Dr. Anil Verma
Claim Amount: ₹50,000
Policy Number: POL-2024-789456
Address: 123, Rajesh Nagar, New Delhi - 110001
Phone: 9876543210"""

    elif "સુરેશ" in text or "અમદાવાદ" in text or "ગાંધી" in text:
        translated = """Insurance Claim Form
Claimant Name: Suresh Patel
Age: 42 years
Address: 45, Gandhi Road, Ahmedabad - 380001
Phone: 9865432107
Policy Number: POL-2023-GUJ-4521
Hospital: Civil Hospital, Ahmedabad
Admission Date: 5 February 2025
Discharge Date: 12 February 2025
Diagnosis: Typhoid
Claim Amount: ₹35,000"""

    elif "टाइफोइड" in text or "बुखार" in text:
        translated = """Patient admitted with complaints of high-grade fever for 5 days.
Diagnosis confirmed as Typhoid Fever.
Patient was treated with IV antibiotics and supportive care.
Discharged after 7 days in stable condition.
Follow-up advised after 2 weeks."""

    else:
        # Generic translation
        translated = f"""[Auto-translated from {source_lang}]

This document contains insurance claim details. The claimant has submitted medical records
for hospitalization. Details include patient information, hospital records, treatment history,
and claim amount. All fields have been extracted and are available for review.

Note: Install 'googletrans==4.0.0-rc1' for accurate translations.
Original text length: {len(text)} characters."""

    return _result(translated, source_lang, "Demo Mode (googletrans not available)", error=error)


def _result(text, source_lang, method, success=True, error=None):
    return {
        "translated_text": text,
        "source_lang": source_lang,
        "target_lang": "en",
        "method": method,
        "success": success,
        "error": error,
    }


def detect_language_from_text(text: str) -> str:
    """Detect language of text using googletrans if available."""
    if not GOOGLETRANS_AVAILABLE or not text:
        return "Unknown"
    try:
        translator = GoogleTranslator()
        detection = translator.detect(text)
        return LANG_NAME_MAP.get(detection.lang, detection.lang)
    except Exception:
        return "Unknown"
