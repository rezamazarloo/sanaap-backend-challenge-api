from document.models import DocumentAuditLog


class AuditLogService:
    @staticmethod
    def record(
        *,
        document,
        action,
        actor,
        metadata=None,
    ) -> DocumentAuditLog:
        if actor is None:
            raise ValueError("Audit log actor is required.")

        return DocumentAuditLog.objects.create(
            document=document,
            action=action,
            actor=actor,
            metadata=metadata or {},
        )
