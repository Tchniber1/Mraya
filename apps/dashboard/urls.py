from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("history/", views.history, name="history"),
    path("products/<str:product_id>/status/", views.product_status, name="product_status"),
    path("<str:analysis_id>/", views.detail, name="detail"),
    path("<str:analysis_id>/delete/", views.delete, name="delete"),
    path("<str:analysis_id>/export.csv", views.export_csv, name="export_csv"),
    path("<str:analysis_id>/export/print/", views.export_print, name="export_print"),
]
