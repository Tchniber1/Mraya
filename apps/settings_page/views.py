from django.contrib import messages
from django.shortcuts import redirect, render

from apps.accounts.session import login_required
from apps.analysis.images import avatar_data_uri
from apps.core.theme import remember_theme
from apps.dashboard.services import invalidate_dashboard
from apps.storage import get_repository

from .forms import AvatarForm, SettingsForm


def _initial(user, session_user):
    return {
        "display_name": user.get("display_name") or session_user.get("name", ""),
        "gender": user.get("gender") or "men",
        "country": user.get("country") or "ma",
        "currency": user.get("currency") or "MAD",
    }


@login_required
def index(request):
    uid = request.mraya_user["uid"]
    repo = get_repository()
    user = repo.get_user(uid) or {}
    form, avatar_form, status = SettingsForm(initial=_initial(user, request.mraya_user)), AvatarForm(), 200

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "remove_avatar":
            repo.save_user(uid, {"avatar": ""})
            invalidate_dashboard(uid)  # the cached dashboard carries the user doc (header avatar)
            messages.success(request, "Profile picture removed.")
            return redirect("settings_page:index")
        if action == "upload_avatar":
            avatar_form = AvatarForm(request.POST, request.FILES)
            if avatar_form.is_valid():
                repo.save_user(uid, {"avatar": avatar_data_uri(avatar_form.cleaned_data["avatar"])})
                invalidate_dashboard(uid)
                messages.success(request, "Profile picture updated.")
                return redirect("settings_page:index")
            status = 400
        elif action == "save":
            form = SettingsForm(request.POST)
            if form.is_valid():
                repo.save_user(uid, form.cleaned_data)
                session_user = request.session.get("mraya_user") or {}
                session_user["name"] = form.cleaned_data["display_name"]
                request.session["mraya_user"] = session_user
                invalidate_dashboard(uid)
                messages.success(request, "Settings saved.")
                return remember_theme(request, redirect("settings_page:index"), form.cleaned_data["gender"])
            status = 400

    request.mraya_profile = repo.get_user(uid) or {}
    return render(request, "settings_page/settings.html",
                  {"form": form, "avatar_form": avatar_form, "user_doc": request.mraya_profile}, status=status)
