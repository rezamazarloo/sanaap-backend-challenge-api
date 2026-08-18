# challenge overview

API implementation using **Django REST Framework** for a document management system providing secure document upload, access control, and retrieval capabilities.

## Features

### Secure & Efficient Document Storage

- Full API for uploading, updating, retrieving, and securely deleting documents
- Document storage using **MinIO**
- User authentication (username & password)
- Role-Based Access Control (**RBAC**):
  - `admin`: Full access (create users, assign roles, manage all documents)
  - `editor`: Upload and update documents (no delete permission)
  - `viewer`: Read-only access to documents
- Secure document URLs
- Filtering and Pagination

### Code Quality

- Adherence to **SOLID** principles
- **Unit Tests** implemented

### Documentation

- API documentation with **Swagger**
- Complete **README** file

## Deployment with Docker

The project is fully dockerized and includes a `docker-compose` setup to run:

- Django backend
- PostgreSQL database
- Redis (for caching)
- MinIO (for object storage)

The deployment guide covers secure environment configuration and managing database migrations inside the container.

## Additional Challenges (Optional)

- Background task processing for document storage
- Audit logging for document access and changes
- Reverse proxy setup using Nginx or Gunicorn
- Real-time notifications via Django Channels and WebSocket when documents are created or updated

## Tech Stack

Django · Django REST Framework · PostgreSQL · Redis · MinIO · Docker
