from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("products/<str:product_id>/status/", views.product_status, name="product_status"),
]
