import csv
import json

from django.contrib import messages
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.session import login_required
from apps.storage import get_repository

from . import export, services
from .services import STATUS_LABELS, StatusError, build_dashboard, change_product_status


def _render_plan(request, analysis_id=None):
    data = build_dashboard(request.mraya_user["uid"], analysis_id)
    if not data["analysis"]:
        if analysis_id:
            raise Http404("Analysis not found")
        return redirect("core:home")
    request.mraya_profile = data["user"]  # lets the theme follow the saved gender
    return render(request, "dashboard/dashboard.html", {**data, "status_labels": STATUS_LABELS})


@login_required
def home(request):
    return _render_plan(request)


@login_required
def detail(request, analysis_id):
    return _render_plan(request, analysis_id)


@login_required
def history(request):
    items = services.history(request.mraya_user["uid"])
    return render(request, "dashboard/history.html", {"analyses": items})


@require_POST
@login_required
def delete(request, analysis_id):
    remaining = services.delete_analysis(request.mraya_user["uid"], analysis_id)
    if remaining is None:
        raise Http404("Analysis not found")
    messages.success(request, "Analysis deleted.")
    return redirect("dashboard:home" if remaining else "core:home")


def _analysis_and_products(request, analysis_id):
    repo = get_repository()
    uid = request.mraya_user["uid"]
    analysis = repo.get_analysis(uid, analysis_id)
    if analysis is None:
        raise Http404("Analysis not found")
    return analysis, repo.list_products(uid, analysis_id)


@login_required
def export_csv(request, analysis_id):
    analysis, products = _analysis_and_products(request, analysis_id)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="mraya-buying-list-{analysis["created_at"][:10]}.csv"'
    response.write("﻿")  # lets Excel read accents and Arabic correctly
    csv.writer(response, lineterminator="\n").writerows(export.export_rows(products))
    return response


@login_required
def export_print(request, analysis_id):
    analysis, products = _analysis_and_products(request, analysis_id)
    items = export.exportable(products)
    currency = (analysis.get("budget") or {}).get("currency") or (items[0]["currency"] if items else "")
    return render(request, "dashboard/print.html", {
        "analysis": analysis, "items": items, "total": export.total(products), "currency": currency,
        "status_labels": export.EXPORT_STATUS_LABELS,
    })


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
