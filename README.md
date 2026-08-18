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

## Document API

- `GET /api/v1/documents/` lists accessible documents.
- `POST /api/v1/documents/` uploads a document for the authenticated user.
- `GET /api/v1/documents/users/<user_id>/` lists documents owned by a user.
- `POST /api/v1/documents/users/<user_id>/` uploads a document for a user.
- `GET /api/v1/documents/<document_id>/` returns metadata and a presigned download URL.
- `PUT /api/v1/documents/<document_id>/` updates document metadata.
- `DELETE /api/v1/documents/<document_id>/` deletes a document.

## Document Type API

- `GET/POST /api/v1/documents/types/`
- `GET/PUT/DELETE /api/v1/documents/types/<document_type_id>/`
