from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from apps.accounts.session import login_required
from apps.onboarding.forms import OnboardingForm, initial_from_user
from apps.storage import get_repository

from .theme import THEMES, remember_theme


@login_required
def home(request):
    """Main page: gender choice first, then photos + profile form."""
    user = get_repository().get_user(request.mraya_user["uid"]) or {}
    request.mraya_profile = user
    form = OnboardingForm(initial=initial_from_user(user))
    return render(request, "core/home.html", {"form": form, "user_doc": user})


@require_POST
def set_theme(request):
    theme = request.POST.get("theme", "")
    if theme not in THEMES:
        return JsonResponse({"error": "Unknown theme"}, status=400)
    return remember_theme(request, JsonResponse({"theme": theme}), theme)
