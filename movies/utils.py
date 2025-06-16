import re
from unidecode import unidecode

# Allow only Latin letters, digits, and spaces
_safe_re = re.compile(r"[^a-z0-9 ]")
# Collapse consecutive whitespace characters into a single space
_space_re = re.compile(r"\s+")
# Replace dash-like characters with a space before transliteration
_dash_re = re.compile(r"[‐‑‒–—―-]+")

def normalize(text: str) -> str:
    """
    Normalize a string by removing diacritical marks and converting it to lowercase ASCII,
    and keeping only Latin letters and digits.

    Args:
        text (str): The input string to normalize.

    Retrurns:
        str: A normalized ASCII-only lowercase version of the input string,
             containing only Latin letters and digits
    """
    text_with_spaces = _dash_re.sub(" ", text)
    ascii_text = unidecode(text_with_spaces).lower()
    ascii_text = _space_re.sub(" ", ascii_text)         # normalize all whitespace to single space
    cleaned = _safe_re.sub("", ascii_text)
    return  _space_re.sub(" ", cleaned).strip()