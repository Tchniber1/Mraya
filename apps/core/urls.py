from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("theme/", views.set_theme, name="set_theme"),
]
