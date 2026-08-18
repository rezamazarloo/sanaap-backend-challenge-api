# sanaap-backend-challenge-api

Document Management System (DMS) with Django REST Framework

## Management Commands

Run migrations first so Django auth permissions exist:

```powershell
uv run python dms/manage.py migrate
```

Create a superuser:

```powershell
uv run python dms/manage.py createsuperuser
```

Create the default RBAC groups and permissions:

```powershell
uv run python dms/manage.py bootstrap_roles
```

Seed the initial document types:

```powershell
uv run python dms/manage.py seed_document_types
```
