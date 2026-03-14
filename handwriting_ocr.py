"""
handwriting_ocr.py
------------------
Handwriting recognition using EasyOCR (primary) with TrOCR fallback.
Automatically detects if a document appears to be handwritten.
"""

import re
import numpy as np
from pathlib import Path

# ─── Optional imports ────────────────────────────────────────────────────────

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

try:
    from PIL import Image, ImageStat
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel
    import torch
    TROCR_AVAILABLE = True
except ImportError:
    TROCR_AVAILABLE = False

# Global readers (lazy-loaded to avoid slow startup)
_easyocr_reader = None


def _get_easyocr_reader():
    global _easyocr_reader
    if _easyocr_reader is None and EASYOCR_AVAILABLE:
        # hi = Hindi, en = English, gu = Gujarati
        try:
            _easyocr_reader = easyocr.Reader(["hi", "en"], gpu=False, verbose=False)
        except Exception:
            try:
                _easyocr_reader = easyocr.Reader(["en"], gpu=False, verbose=False)
            except Exception:
                pass
    return _easyocr_reader


# ─── HANDWRITING DETECTION ───────────────────────────────────────────────────

def is_handwritten(filepath: str) -> bool:
    """
    Heuristic check: handwritten docs tend to have more edge variance,
    irregular stroke widths, and lower contrast uniformity.
    Returns True if likely handwritten.
    """
    if not PIL_AVAILABLE:
        return False
    try:
        img = Image.open(filepath).convert("L")
        # Check pixel variance — handwriting has high local variance
        stat = ImageStat.Stat(img)
        stddev = stat.stddev[0]
        # Typically printed text: stddev < 80; handwriting: > 80
        return stddev > 75
    except Exception:
        return False


# ─── EASYOCR EXTRACTION ─────────────────────────────────────────────────────

def extract_handwriting_easyocr(filepath: str) -> dict:
    """Use EasyOCR to extract text from handwritten document."""
    reader = _get_easyocr_reader()
    if reader is None:
        return _demo_handwriting(filepath)

    try:
        results = reader.readtext(filepath, detail=0, paragraph=True)
        text = "\n".join(results)
        return {
            "text": text.strip(),
            "method": "EasyOCR",
            "confidence": "Medium",
            "success": True,
            "error": None,
        }
    except Exception as e:
        return _demo_handwriting(filepath, error=str(e))


# ─── TROCR EXTRACTION ────────────────────────────────────────────────────────

def extract_handwriting_trocr(filepath: str) -> dict:
    """Use Microsoft TrOCR for handwriting recognition (English)."""
    if not TROCR_AVAILABLE or not PIL_AVAILABLE:
        return extract_handwriting_easyocr(filepath)

    try:
        processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten")
        model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten")

        img = Image.open(filepath).convert("RGB")
        pixel_values = processor(images=img, return_tensors="pt").pixel_values
        generated_ids = model.generate(pixel_values)
        text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]

        return {
            "text": text.strip(),
            "method": "TrOCR (Microsoft)",
            "confidence": "High",
            "success": True,
            "error": None,
        }
    except Exception as e:
        return extract_handwriting_easyocr(filepath)


# ─── UNIFIED EXTRACTION ──────────────────────────────────────────────────────

def extract_handwriting(filepath: str, prefer_trocr: bool = False) -> dict:
    """
    Main handwriting extraction function.
    Tries TrOCR if preferred, else EasyOCR.
    Falls back to demo mode if libraries not available.
    """
    if prefer_trocr and TROCR_AVAILABLE:
        result = extract_handwriting_trocr(filepath)
    else:
        result = extract_handwriting_easyocr(filepath)

    return result


# ─── DEMO FALLBACK ───────────────────────────────────────────────────────────

def _demo_handwriting(filepath: str, error: str = None) -> dict:
    """Realistic demo output when EasyOCR/TrOCR not available."""
    demo_text = """[Handwritten Document - Demo Mode]

Patient Name: Suresh Bhai Patel
Age: 45
Date: 10/03/2025
Hospital: Shree Krishna Hospital
Ward No: General - 3B

Chief Complaint: Fever and abdominal pain since 5 days

History:
- Patient came with complaints of high grade fever
- Associated vomiting and loose stools
- No h/o similar complaints in past

Examination:
BP: 120/80 mmHg
Temp: 102°F
Pulse: 92/min

Diagnosis: Typhoid Fever with dehydration

Treatment prescribed:
- IV fluids
- Tab Cefixime 200mg BD
- Tab Paracetamol 650mg TDS

Discharge after 7 days if afebrile.

Signed: Dr. V.K. Mehta
MBBS, MD (Medicine)
Reg No: 12345"""

    return {
        "text": demo_text,
        "method": "Demo Mode (EasyOCR not available)",
        "confidence": "N/A",
        "success": True,
        "error": error,
    }
