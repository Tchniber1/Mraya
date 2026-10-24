import json
import logging

from django.conf import settings
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.storage import get_repository

from . import firebase
from .session import current_user, login_user, logout_user

logger = logging.getLogger("apps.accounts")

DEMO_UID = "demo-user"


def _after_login_url(uid):
    user = get_repository().get_user(uid)
    return "/dashboard/" if user and user.get("has_analysis") else "/"


def login_page(request):
    if current_user(request):
        return redirect("core:home")
    return render(
        request,
        "accounts/login.html",
        {
            "firebase_config": {**settings.FIREBASE_WEB_CONFIG, "googleClientId": settings.GOOGLE_OAUTH_CLIENT_ID},
            "firebase_enabled": settings.FIREBASE_AUTH_ENABLED,
            "dev_login": settings.MRAYA_DEV_LOGIN,
        },
    )


@require_POST
def firebase_session(request):
    """Exchange a Firebase ID token (from Google sign-in) for a Django session."""
    try:
        token = json.loads(request.body or b"{}").get("idToken", "")
    except ValueError:
        token = ""
    if not token:
        return JsonResponse({"error": "Missing token"}, status=400)
    try:
        claims = firebase.verify_id_token(token)
    except Exception:  # invalid/expired token, misconfiguration, network...
        logger.exception("Firebase token verification failed")
        return JsonResponse({"error": "Could not verify your Google sign-in"}, status=401)

    uid = claims["uid"]
    profile = {
        "email": claims.get("email", ""),
        "name": claims.get("name", ""),
        "picture": claims.get("picture", ""),
    }
    repo = get_repository()
    existing = repo.get_user(uid) or {}
    saved = repo.save_user(uid, {
        "email": profile["email"],
        "display_name": existing.get("display_name") or profile["name"],  # keep a name changed in Settings
        "google_picture": profile["picture"],
    })
    login_user(request, uid, gender=saved.get("gender", ""), **profile)
    return JsonResponse({"redirect": _after_login_url(uid)})


@require_POST
def dev_login(request):
    if not settings.MRAYA_DEV_LOGIN:
        raise Http404
    saved = get_repository().save_user(DEMO_UID, {"email": "demo@mraya.local", "display_name": "Demo User"})
    login_user(request, DEMO_UID, email="demo@mraya.local", name="Demo User", gender=saved.get("gender", ""))
    return redirect(_after_login_url(DEMO_UID))


@require_POST
def logout(request):
    logout_user(request)
    response = redirect("accounts:login")
    response.delete_cookie(settings.THEME_COOKIE_NAME)
    return response
