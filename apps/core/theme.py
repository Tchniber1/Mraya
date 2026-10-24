"""Which colour theme to show: men, women, or the neutral starting palette."""
from django.conf import settings

THEMES = ("neutral", "men", "women")


def normalise_theme(value):
    return value if value in THEMES else "neutral"


def resolve_theme(request):
    user = request.session.get("mraya_user") or {}
    if user.get("gender") in THEMES:
        return user["gender"]
    stored = getattr(request, "mraya_profile", None) or {}
    if stored.get("gender") in THEMES:
        return stored["gender"]
    return normalise_theme(request.COOKIES.get(settings.THEME_COOKIE_NAME, ""))


def remember_theme(request, response, theme):
    """Persist the theme in the session (signed-in user) and a long-lived cookie."""
    theme = normalise_theme(theme)
    user = request.session.get("mraya_user")
    if user is not None:
        user["gender"] = theme
        request.session["mraya_user"] = user
    response.set_cookie(
        settings.THEME_COOKIE_NAME, theme, max_age=settings.SESSION_COOKIE_AGE, samesite="Lax"
    )
    return response
