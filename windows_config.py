"""
windows_config.py
-----------------
Windows-specific configuration for InvestiAI.
Auto-detects Tesseract installation path and sets it for pytesseract.

Import this at the top of ocr_engine.py when running on Windows.
"""

import os
import sys
import platform
from pathlib import Path


def configure_tesseract_windows():
    """
    Auto-detect and configure Tesseract OCR path on Windows.
    Tries common installation paths. Returns True if found.
    """
    if platform.system() != "Windows":
        return True  # Not needed on macOS/Linux

    try:
        import pytesseract
    except ImportError:
        return False

    # Common Tesseract install locations on Windows
    candidate_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Users\{user}\AppData\Local\Programs\Tesseract-OCR\tesseract.exe".format(
            user=os.environ.get("USERNAME", "")
        ),
        r"C:\tesseract\tesseract.exe",
        r"D:\Tesseract-OCR\tesseract.exe",
    ]

    # Check if tesseract is already in PATH
    import shutil
    if shutil.which("tesseract"):
        return True  # Already in PATH, no config needed

    # Try candidate paths
    for path in candidate_paths:
        if Path(path).exists():
            pytesseract.pytesseract.tesseract_cmd = path
            return True

    # Check environment variable
    env_path = os.environ.get("TESSERACT_PATH", "")
    if env_path and Path(env_path).exists():
        pytesseract.pytesseract.tesseract_cmd = env_path
        return True

    return False


def configure_poppler_windows():
    """
    Add Poppler bin directory to PATH on Windows for pdf2image support.
    Returns True if Poppler is found.
    """
    if platform.system() != "Windows":
        return True

    candidate_dirs = [
        r"C:\poppler\bin",
        r"C:\poppler-windows\bin",
        r"C:\Program Files\poppler\bin",
        r"C:\Users\{user}\poppler\bin".format(user=os.environ.get("USERNAME", "")),
    ]

    env_path = os.environ.get("POPPLER_PATH", "")
    if env_path:
        candidate_dirs.insert(0, env_path)

    for d in candidate_dirs:
        if Path(d).exists():
            os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")
            return True

    return False


def get_system_info() -> dict:
    """Return system information for the Settings page."""
    info = {
        "os": platform.system(),
        "os_version": platform.version(),
        "python": sys.version.split()[0],
        "tesseract": False,
        "tesseract_path": "",
        "poppler": False,
    }

    try:
        import pytesseract
        configure_tesseract_windows()
        ver = pytesseract.get_tesseract_version()
        info["tesseract"] = True
        info["tesseract_version"] = str(ver)
        info["tesseract_path"] = pytesseract.pytesseract.tesseract_cmd
    except Exception:
        pass

    try:
        import shutil
        if shutil.which("pdftoppm"):
            info["poppler"] = True
    except Exception:
        pass

    return info


# ── Auto-configure when this module is imported ───────────────────────────────
if platform.system() == "Windows":
    configure_tesseract_windows()
    configure_poppler_windows()
