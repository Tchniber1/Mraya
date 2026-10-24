"""XP and level rules. Pure functions: no Django, no storage."""

XP_EVENTS = {
    "profile_completed": 50,
    "analysis_completed": 100,
    "product_started": 40,
    "product_feedback": 5,  # "not interested" still teaches Mraya your taste
}

# Product status -> XP event it unlocks (each product awards each event once).
STATUS_EVENTS = {
    "started": "product_started",
    "not_interested": "product_feedback",
}

LEVEL_TITLES = [
    "Style Rookie",
    "Trend Seeker",
    "Look Builder",
    "Style Curator",
    "Icon in the Making",
    "Mraya Icon",
]


def xp_threshold(level):
    """Total XP needed to reach ``level`` (level 1 = 0 XP, then 100, 300, 600, ...)."""
    level = max(1, int(level))
    return 50 * level * (level - 1)


def level_for(xp):
    xp = max(0, int(xp or 0))
    level = 1
    while xp >= xp_threshold(level + 1):
        level += 1
    floor_xp = xp_threshold(level)
    next_xp = xp_threshold(level + 1)
    span = next_xp - floor_xp
    return {
        "xp": xp,
        "level": level,
        "title": LEVEL_TITLES[min(level, len(LEVEL_TITLES)) - 1],
        "xp_into_level": xp - floor_xp,
        "xp_for_next": span,
        "xp_to_next": next_xp - xp,
        "progress_pct": round(100 * (xp - floor_xp) / span),
    }


def xp_for_status_change(product, new_status):
    """Return (event_name, xp) for moving ``product`` to ``new_status``, or (None, 0)."""
    event = STATUS_EVENTS.get(new_status)
    if not event or event in product.get("xp_events", []):
        return None, 0
    return event, XP_EVENTS[event]
