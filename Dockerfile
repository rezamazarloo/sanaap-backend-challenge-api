FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .

FROM python:3.13-slim-bookworm

ARG DOCUMENT_LOCAL_STORAGE=local_uploads

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HOME=/home/django
ENV PATH="/app/.venv/bin:$PATH"
ENV DOCUMENT_LOCAL_STORAGE=${DOCUMENT_LOCAL_STORAGE}

WORKDIR /app

RUN addgroup --system django \
    && adduser --system --ingroup django --home /home/django django

COPY --from=builder --chown=django:django /app /app

RUN mkdir -p "/app/dms/${DOCUMENT_LOCAL_STORAGE}/documents" \
    && chown -R django:django "/app/dms/${DOCUMENT_LOCAL_STORAGE}" \
    && chmod +x /app/docker/entrypoint.sh

WORKDIR /app/dms

USER django

EXPOSE 8000 8001

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-"]
