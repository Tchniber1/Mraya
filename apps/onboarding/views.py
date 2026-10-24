import logging

from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.session import login_required
from apps.analysis import images
from apps.analysis.service import AnalysisFailed, run_analysis
from apps.core.theme import remember_theme
from apps.dashboard.services import invalidate_dashboard
from apps.progress.rules import XP_EVENTS
from apps.storage import get_repository

from .forms import OnboardingForm

logger = logging.getLogger("apps.onboarding")


@require_POST
@login_required
def analyze(request):
    uid = request.mraya_user["uid"]
    repo = get_repository()
    form = OnboardingForm(request.POST, request.FILES)
    if not form.is_valid():
        return render(request, "core/home.html", {"form": form, "user_doc": repo.get_user(uid) or {}}, status=400)

    profile = form.profile()
    body, face = form.cleaned_data["full_body"], form.cleaned_data["face"]
    try:
        analysis, products = run_analysis(profile, images.for_ai(body), images.for_ai(face))
    except AnalysisFailed as exc:
        form.add_error(None, str(exc))
        return render(request, "core/home.html", {"form": form, "user_doc": repo.get_user(uid) or {}}, status=502)

    existing = repo.get_user(uid) or {}
    thumbs = {"body_thumb": images.thumbnail_data_uri(body), "face_thumb": images.thumbnail_data_uri(face)}
    repo.save_user(
        uid,
        {
            **profile,
            **thumbs,
            "has_analysis": True,
            "profile_xp_awarded": True,
        },
    )
    repo.add_analysis(uid, {**analysis, **thumbs}, products)

    gained = XP_EVENTS["analysis_completed"]
    if not existing.get("profile_xp_awarded"):
        gained += XP_EVENTS["profile_completed"]
    repo.increment_xp(uid, gained)
    invalidate_dashboard(uid)

    messages.success(request, f"Your style plan is ready! +{gained} XP")
    return remember_theme(request, redirect("dashboard:home"), profile["gender"])
