import json

from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.session import login_required

from .services import STATUS_LABELS, StatusError, build_dashboard, change_product_status


@login_required
def home(request):
    data = build_dashboard(request.mraya_user["uid"])
    if not data["analysis"]:
        return redirect("core:home")
    request.mraya_profile = data["user"]  # lets the theme follow the saved gender
    return render(request, "dashboard/dashboard.html", {**data, "status_labels": STATUS_LABELS})


@require_POST
@login_required
def product_status(request, product_id):
    try:
        status = json.loads(request.body or b"{}").get("status", "")
    except ValueError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    try:
        result = change_product_status(request.mraya_user["uid"], product_id, status)
    except StatusError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(result)
