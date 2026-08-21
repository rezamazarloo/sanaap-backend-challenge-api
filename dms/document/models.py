from django.conf import settings
from django.db import models


class DocumentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    READY = "ready", "Ready"
    FAILED = "failed", "Failed"


class Action(models.TextChoices):
    CREATED = "created", "Created"
    DOWNLOAD_LINK_GENERATED = "download_link_generated", "Download link generated"
    REPLACED = "replaced", "Replaced"
    DELETED = "deleted", "Deleted"


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
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="documents",
    )
    original_filename = models.CharField(max_length=255)
    object_key = models.CharField(max_length=500, unique=True)
    local_file_path = models.CharField(max_length=500, blank=True)
    content_type = models.CharField(max_length=100)
    size = models.PositiveBigIntegerField()
    checksum = models.CharField(max_length=64)
    status = models.CharField(
        max_length=20,
        choices=DocumentStatus.choices,
        default=DocumentStatus.PENDING,
        db_index=True,
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_documents",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        permissions = [
            ("add_image_document", "Can add image documents"),
            ("change_image_document", "Can change image documents"),
        ]

    def __str__(self):
        return self.original_filename


class DocumentAuditLog(models.Model):
    document = models.ForeignKey(
        Document,
        on_delete=models.SET_NULL,
        related_name="document_audit_logs",
        null=True,
        blank=True,
    )
    action = models.CharField(
        max_length=32,
        choices=Action.choices,
        db_index=True,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="document_audit_logs",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} document audit log"
