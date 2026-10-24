from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_page, name="login"),
    path("session/", views.firebase_session, name="firebase_session"),
    path("dev-login/", views.dev_login, name="dev_login"),
    path("logout/", views.logout, name="logout"),
]
