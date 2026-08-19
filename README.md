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

## Account API

- `POST /api/v1/account/auth/signup/` creates a public user account with `username` and `password`.
- `POST /api/v1/account/auth/login/` returns an authentication token for `username` and `password`.
- `POST /api/v1/account/auth/logout/` deletes the authenticated user's token.
- `GET /api/v1/account/users/` lists users; requires `auth.view_user`.
- `POST /api/v1/account/users/` creates a user; requires `auth.add_user`.
- `GET /api/v1/account/users/<user_id>/` returns one user with group membership; requires `auth.view_user`.
- `POST /api/v1/account/users/<user_id>/assign-group/` assigns a user to a group with `group_id`; requires `auth.change_user`.
- `GET /api/v1/account/groups/` lists available groups; requires `auth.view_group`.

## Document API

- `GET /api/v1/documents/` lists documents owned by the authenticated user.
- `POST /api/v1/documents/` uploads a document for the authenticated user.
- `GET /api/v1/documents/all/` lists all documents for users with `document.view_document`.
- `POST /api/v1/documents/users/<user_id>/` uploads a document for a user; requires `document.add_document`.
- `GET /api/v1/documents/<document_id>/` returns metadata and a presigned download URL.
- `PUT /api/v1/documents/<document_id>/` replaces the stored file.
- `DELETE /api/v1/documents/<document_id>/` deletes a document.

## Document Type API

- `GET/POST /api/v1/documents/types/`
- `GET/PUT/DELETE /api/v1/documents/types/<document_type_id>/`
