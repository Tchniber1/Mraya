from django.conf import settings
from django.urls import include, path

from config.plugins import plugin_urlpatterns

urlpatterns = [
    path("", include("apps.core.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("onboarding/", include("apps.onboarding.urls")),
    path("dashboard/", include("apps.dashboard.urls")),
    *plugin_urlpatterns(settings.MRAYA_PLUGIN_APPS),
]
