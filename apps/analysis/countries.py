"""Countries the user can shop from, their default currency, and where to look abroad."""

COUNTRIES = {
    "ma": "Morocco", "fr": "France", "es": "Spain", "be": "Belgium", "gb": "United Kingdom",
    "us": "United States", "ca": "Canada", "ae": "United Arab Emirates", "sa": "Saudi Arabia",
    "de": "Germany", "it": "Italy", "nl": "Netherlands",
}

DEFAULT_CURRENCY = {
    "ma": "MAD", "fr": "EUR", "es": "EUR", "be": "EUR", "de": "EUR", "it": "EUR", "nl": "EUR",
    "gb": "GBP", "us": "USD", "ca": "CAD", "ae": "AED", "sa": "SAR",
}

ABROAD_ORDER = {"ma": ["fr", "us"]}


def abroad_countries(code):
    """Where to search when a product isn't sold in ``code`` (never ``code`` itself)."""
    return [c for c in ABROAD_ORDER.get(code, ["us"]) if c != code]


def flag(code):
    return "".join(chr(0x1F1E6 + ord(ch) - ord("a")) for ch in (code or "").lower()[:2])
