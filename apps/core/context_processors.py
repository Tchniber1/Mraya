from django.conf import settings

from apps.storage import get_repository

from .theme import resolve_theme


def _initials(name):
    parts = [p for p in name.split() if p]
    return "".join(p[0] for p in parts[:2]).upper() or "M"


def mraya(request):
    user = request.session.get("mraya_user")
    name = (user or {}).get("name") or ""
    doc = getattr(request, "mraya_profile", None)
    if user and doc is None:
        doc = get_repository().get_user(user["uid"]) or {}
    doc = doc or {}
    return {
        "avatar_url": doc.get("avatar") or doc.get("google_picture") or (user or {}).get("picture") or "",
        "initials": _initials(doc.get("display_name") or name),
        "theme": resolve_theme(request),
        "mraya_user": user,
        "first_name": name.split()[0] if name.strip() else "",
        "gemma_model": settings.GEMMA_MODEL,
    }
