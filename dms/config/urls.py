from django.conf import settings
from django.urls import include, path

urlpatterns = [
    path("api/v1/account/", include("account.urls", namespace="account")),
    path(
        "api/v1/backoffice/",
        include("backoffice.urls", namespace="backoffice"),
    ),
    path("api/v1/documents/", include("document.urls", namespace="document")),
]


if settings.DEBUG:
    from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

    urlpatterns += [
        path("schema/", SpectacularAPIView.as_view(), name="schema"),
        path("docs/", SpectacularSwaggerView.as_view(url_name="schema")),
    ]
