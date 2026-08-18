from django.urls import path
from document.views import DocumentDownloadDeleteView, DocumentListCreateView

app_name = "document"

urlpatterns = [
    path("", DocumentListCreateView.as_view(), name="document-list-create"),
    path(
        "<int:document_id>/",
        DocumentDownloadDeleteView.as_view(),
        name="document-download-delete",
    ),
]
