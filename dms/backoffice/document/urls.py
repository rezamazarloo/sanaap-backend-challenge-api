from backoffice.document.views import (
    BackofficeDocumentAuditLogListView,
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
        "audits/",
        BackofficeDocumentAuditLogListView.as_view(),
        name="document-audit-log-list",
    ),
    path(
        "<int:document_id>/",
        BackofficeDocumentDetailUpdateDeleteView.as_view(),
        name="document-detail-update-delete",
    ),
]
