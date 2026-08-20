from django.urls import include, path

app_name = "backoffice"

urlpatterns = [
    path(
        "documents/",
        include("backoffice.document.urls", namespace="document"),
    ),
]
