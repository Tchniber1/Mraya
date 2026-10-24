"""Builds (and caches) everything the dashboard needs; applies product status changes."""
from django.core.cache import cache

from apps.analysis.countries import COUNTRIES, flag
from apps.analysis.prompts import CATEGORIES
from apps.progress.rules import level_for, xp_for_status_change
from apps.storage import get_repository
from apps.storage.base import PRODUCT_STATUSES

STATUS_LABELS = {
    "suggested": "New",
    "started": "Bought / started",
    "not_yet": "Not yet",
    "not_interested": "Not for me",
}

CATEGORY_ICONS = {
    "clothing": "shirt", "hair": "scissors", "skincare": "droplet",
    "perfume": "sparkles", "shoes": "footprints", "accessories": "watch",
}


def _version(uid):
    return cache.get(f"mraya:dashver:{uid}", 0)


def _key(uid, analysis_id):
    return f"mraya:dashboard:{uid}:{_version(uid)}:{analysis_id or 'latest'}"


def invalidate_dashboard(uid):
    """Forget every cached dashboard of this user (bumps a per-user version)."""
    cache.set(f"mraya:dashver:{uid}", _version(uid) + 1, None)


def _decorate(product):
    country = product.get("origin_country") or ""
    return {
        **product,
        "icon": CATEGORY_ICONS.get(product.get("category"), "sparkles"),
        "approx": bool(product.get("price_converted")) or product.get("price_source") == "estimate",
        "flag": flag(country) if country else "",
        "country_name": COUNTRIES.get(country, country.upper()),
    }


def build_dashboard(uid, analysis_id=None):
    """Data for one analysis (the latest when ``analysis_id`` is None); ``analysis`` is None if missing."""
    key = _key(uid, analysis_id)
    cached = cache.get(key)
    if cached is not None:
        return cached

    repo = get_repository()
    user = repo.get_user(uid) or {}
    analysis = repo.get_analysis(uid, analysis_id) if analysis_id else repo.latest_analysis(uid)
    products = [_decorate(p) for p in repo.list_products(uid, analysis["id"])] if analysis else []

    local = [p for p in products if p.get("origin") != "abroad"]
    abroad = [p for p in products if p.get("origin") == "abroad"]
    advice = {c["category"]: c["advice"] for c in (analysis or {}).get("categories", [])}
    groups = []
    for cat, label in CATEGORIES.items():
        items = [p for p in local if p["category"] == cat]
        has_any = items or any(p["category"] == cat for p in abroad)
        if items or (cat in advice and not has_any):
            groups.append({"key": cat, "label": label, "icon": CATEGORY_ICONS[cat],
                           "advice": advice.get(cat, ""), "products": items, "empty": not items})

    counts = {status: 0 for status in PRODUCT_STATUSES}
    for product in products:
        status = product.get("status", "suggested")
        counts[status] = counts.get(status, 0) + 1

    budget = (analysis or {}).get("budget")
    budget_pct = min(100, round(100 * budget["used"] / budget["limit"])) if budget and budget.get("limit") else 0

    data = {
        "user": user,
        "analysis": analysis,
        "photos": {
            "body": (analysis or {}).get("body_thumb") or user.get("body_thumb", ""),
            "face": (analysis or {}).get("face_thumb") or user.get("face_thumb", ""),
        },
        "groups": groups,
        "abroad": abroad,
        "home_country": COUNTRIES.get(user.get("country") or "ma", "your country"),
        "counts": counts,
        "total_products": len(products),
        "budget": budget,
        "budget_pct": budget_pct,
        "progress": level_for(user.get("xp", 0)),
    }
    cache.set(key, data)
    return data


def history(uid):
    repo = get_repository()
    user = repo.get_user(uid) or {}
    items = []
    for analysis in repo.list_analyses(uid):
        items.append({
            **analysis,
            "body": analysis.get("body_thumb") or user.get("body_thumb", ""),
            "face": analysis.get("face_thumb") or user.get("face_thumb", ""),
        })
    return items


def delete_analysis(uid, analysis_id):
    """Delete one analysis. Returns None if it didn't exist, else whether any analysis is left."""
    repo = get_repository()
    if not repo.delete_analysis(uid, analysis_id):
        return None
    remaining = repo.latest_analysis(uid) is not None
    if not remaining:
        repo.save_user(uid, {"has_analysis": False})
    invalidate_dashboard(uid)
    return remaining


class StatusError(ValueError):
    pass


def change_product_status(uid, product_id, status):
    if status not in PRODUCT_STATUSES:
        raise StatusError("Unknown status")
    repo = get_repository()
    product = repo.get_product(uid, product_id)
    if product is None:
        raise StatusError("Product not found")

    event, xp = xp_for_status_change(product, status)
    fields = {"status": status}
    if event:
        fields["xp_events"] = [*product.get("xp_events", []), event]
    repo.update_product(uid, product_id, fields)
    total = repo.increment_xp(uid, xp) if xp else int((repo.get_user(uid) or {}).get("xp", 0))
    invalidate_dashboard(uid)
    return {"status": status, "label": STATUS_LABELS[status], "xp_gained": xp, "progress": level_for(total)}
