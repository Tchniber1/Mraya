"""Price strings from shops -> (amount, ISO code), and fixed-rate conversion."""
import re

from .parser import _number

# MAD per one unit of each currency (fixed demo rates, not live).
RATES_TO_MAD = {"MAD": 1.0, "EUR": 10.8, "USD": 9.9, "GBP": 12.7, "CAD": 7.2, "AED": 2.7, "SAR": 2.64}

# Checked in order, so "CA$" wins over "$".
_MARKERS = (
    ("CA$", "CAD"), ("C$", "CAD"), ("CAD", "CAD"),
    ("€", "EUR"), ("EUR", "EUR"),
    ("£", "GBP"), ("GBP", "GBP"),
    ("US$", "USD"), ("USD", "USD"), ("$", "USD"),
    ("MAD", "MAD"), ("DHS", "MAD"), ("DH", "MAD"),
    ("AED", "AED"), ("SAR", "SAR"),
)


def parse_price(text):
    amount = _number(text) if text else None
    if amount is None:
        return None, None
    upper = str(text).upper()
    for marker, code in _MARKERS:
        if marker.isalpha():
            if re.search(rf"(?<![A-Z]){marker}(?![A-Z])", upper):
                return amount, code
        elif marker in upper:
            return amount, code
    return amount, None


def convert(amount, from_code, to_code):
    if from_code not in RATES_TO_MAD or to_code not in RATES_TO_MAD:
        return None
    return round(amount * RATES_TO_MAD[from_code] / RATES_TO_MAD[to_code], 2)
