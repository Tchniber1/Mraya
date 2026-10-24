"""Buying-list export: which products go in, and the CSV rows."""
from apps.analysis.prompts import CATEGORIES

EXPORT_STATUS_LABELS = {"started": "Bought", "not_yet": "Not yet", "suggested": "To decide"}
HEADER = ["category", "brand", "name", "price", "currency", "store", "link", "status"]


def exportable(products):
    """Everything except products marked "Not for me"."""
    return [p for p in products if p.get("status", "suggested") in EXPORT_STATUS_LABELS]


def _price(value):
    if value is None:
        return ""
    return str(int(value)) if float(value).is_integer() else f"{value:.2f}"


def _cell(value):
    """Stop spreadsheet apps from running text from shops/the model as a formula."""
    value = str(value or "")
    return "'" + value if value[:1] in ("=", "+", "-", "@", "\t", "\r") else value


def export_rows(products):
    rows = [HEADER]
    for p in exportable(products):
        rows.append([
            CATEGORIES.get(p.get("category"), p.get("category", "")), _cell(p.get("brand")), _cell(p.get("name")),
            _price(p.get("price")), p.get("currency", ""), _cell(p.get("store")), _cell(p.get("link")),
            EXPORT_STATUS_LABELS[p.get("status", "suggested")],
        ])
    return rows


def total(products):
    return round(sum(p["price"] for p in exportable(products) if p.get("price") is not None), 2)
