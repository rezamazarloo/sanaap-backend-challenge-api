from backoffice.document.views import (
    BackofficeDocumentDetailUpdateDeleteView,
    BackofficeDocumentListCreateView,
)
from django.urls import path

app_name = "document"

urlpatterns = [
    path(
        "",
        BackofficeDocumentListCreateView.as_view(),
        name="document-list-create",
    ),
    path(
        "<int:document_id>/",
        BackofficeDocumentDetailUpdateDeleteView.as_view(),
        name="document-detail-update-delete",
    ),
]
