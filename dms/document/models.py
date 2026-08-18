from django.conf import settings
from django.db import models


class DocumentType(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    allowed_extensions = models.JSONField(default=list, blank=True)
    allowed_content_types = models.JSONField(default=list, blank=True)
    max_size_bytes = models.PositiveBigIntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Document(models.Model):
    document_type = models.ForeignKey(
        DocumentType,
        on_delete=models.PROTECT,
        related_name="documents",
    )
    original_filename = models.CharField(max_length=255)
    object_key = models.CharField(max_length=500, unique=True)
    content_type = models.CharField(max_length=100)
    size = models.PositiveBigIntegerField()
    checksum = models.CharField(max_length=64)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_documents",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.original_filename
