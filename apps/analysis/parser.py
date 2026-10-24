"""Turn Gemma's text reply into a clean, predictable analysis + product list."""
import json
import re

from .prompts import CATEGORIES


class AnalysisParseError(ValueError):
    pass


def extract_json(text):
    """Find and decode the outermost JSON object in ``text`` (tolerates fences/prose)."""
    if not text:
        raise AnalysisParseError("Empty reply from the model")
    cleaned = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end <= start:
        raise AnalysisParseError("No JSON object in the model reply")
    try:
        data = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise AnalysisParseError(f"Invalid JSON: {exc}") from None
    if not isinstance(data, dict):
        raise AnalysisParseError("JSON reply is not an object")
    return data


def _text(value, limit=600):
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        value = ", ".join(str(v) for v in value)
    return str(value).strip()[:limit]


def _number(value):
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    match = re.search(r"\d[\d,.\s]*", str(value or ""))
    if not match:
        return None
    raw = re.sub(r"\s", "", match.group()).rstrip(".,")
    if "," in raw and "." in raw:
        raw = raw.replace(",", "")  # 1,299.50
    elif "," in raw:
        # 1,200 / 12,500,000 are thousands; 12,5 is a decimal comma
        raw = raw.replace(",", "") if re.fullmatch(r"\d{1,3}(,\d{3})+", raw) else raw.replace(",", ".")
    try:
        return round(float(raw), 2)
    except ValueError:
        return None


def _steps(value):
    if isinstance(value, str):
        value = [s for s in re.split(r"\n|;", value) if s.strip()]
    if not isinstance(value, list):
        return []
    return [_text(step, 200) for step in value if _text(step)][:8]


CATEGORY_ALIASES = {
    "clothes": "clothing", "outfit": "clothing", "apparel": "clothing", "wardrobe": "clothing",
    "fragrance": "perfume", "cologne": "perfume", "scent": "perfume",
    "footwear": "shoes", "sneakers": "shoes",
    "grooming": "hair", "haircare": "hair", "beard": "hair",
    "skin": "skincare", "jewelry": "accessories", "jewellery": "accessories",
}


def _category_key(raw):
    key = _text(raw).lower()
    if key in CATEGORIES:
        return key
    for name, label in CATEGORIES.items():
        if key.startswith(name[:4]) or label.lower() in key:
            return name
    for alias, name in CATEGORY_ALIASES.items():
        if alias in key:
            return name
    return None


def normalise(data, default_currency):
    """Return ``(analysis, products)`` with every field present and typed."""
    profile = data.get("style_profile") if isinstance(data.get("style_profile"), dict) else {}
    score = _number(data.get("style_score"))
    routine = data.get("routine") if isinstance(data.get("routine"), dict) else {}

    categories, products = [], []
    for block in data.get("categories") or []:
        if not isinstance(block, dict):
            continue
        key = _category_key(block.get("category"))
        if not key:
            continue
        categories.append({"category": key, "label": CATEGORIES[key], "advice": _text(block.get("advice"))})
        for item in block.get("products") or []:
            if not isinstance(item, dict) or not _text(item.get("name")):
                continue
            products.append(
                {
                    "category": key,
                    "name": _text(item.get("name"), 160),
                    "brand": _text(item.get("brand"), 80),
                    "price": _number(item.get("price")),
                    "currency": _text(item.get("currency"), 8).upper() or default_currency,
                    "where_to_buy": _text(item.get("where_to_buy"), 200),
                    "why": _text(item.get("why"), 300),
                }
            )

    if not products:
        raise AnalysisParseError("The model reply contained no products")

    analysis = {
        "summary": _text(data.get("summary"), 1200),
        "style_profile": {
            k: _text(profile.get(k), 160)
            for k in ("body_type", "face_shape", "skin_tone", "hair", "style_archetype")
        },
        "style_score": int(max(0, min(100, score))) if score is not None else None,
        "routine": {"morning": _steps(routine.get("morning")), "evening": _steps(routine.get("evening"))},
        "categories": categories,
    }
    return analysis, products
