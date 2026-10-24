from django.urls import path

from . import views

app_name = "onboarding"

urlpatterns = [
    path("analyze/", views.analyze, name="analyze"),
]
