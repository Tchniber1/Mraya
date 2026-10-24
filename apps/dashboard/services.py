"""Builds (and caches) everything the dashboard needs; applies product status changes."""
from django.core.cache import cache

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


def _key(uid):
    return f"mraya:dashboard:{uid}"


def invalidate_dashboard(uid):
    cache.delete(_key(uid))


def build_dashboard(uid):
    cached = cache.get(_key(uid))
    if cached is not None:
        return cached

    repo = get_repository()
    user = repo.get_user(uid) or {}
    analysis = repo.latest_analysis(uid)
    products = repo.list_products(uid)

    advice = {c["category"]: c["advice"] for c in (analysis or {}).get("categories", [])}
    groups = []
    for key, label in CATEGORIES.items():
        items = [p for p in products if p["category"] == key]
        if items:
            groups.append({"key": key, "label": label, "advice": advice.get(key, ""), "products": items})

    counts = {status: 0 for status in PRODUCT_STATUSES}
    for product in products:
        counts[product.get("status", "suggested")] = counts.get(product.get("status", "suggested"), 0) + 1

    data = {
        "user": user,
        "analysis": analysis,
        "groups": groups,
        "counts": counts,
        "total_products": len(products),
        "progress": level_for(user.get("xp", 0)),
    }
    cache.set(_key(uid), data)
    return data


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
