from django.conf import settings

from .theme import resolve_theme


def mraya(request):
    user = request.session.get("mraya_user")
    name = (user or {}).get("name") or ""
    return {
        "theme": resolve_theme(request),
        "mraya_user": user,
        "first_name": name.split()[0] if name.strip() else "",
        "gemma_model": settings.GEMMA_MODEL,
    }
