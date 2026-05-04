FROM python:3.12-slim AS builder

WORKDIR /app

ENV POETRY_VIRTUALENVS_CREATE=false

COPY pyproject.toml ./
RUN pip install --no-cache-dir poetry \
    && poetry install --only main --no-root --no-interaction --no-ansi

COPY . .

# Build Tailwind CSS in the builder so the runtime image does not need
# the vendored Tailwind binary.
RUN ./bin/tailwindcss -i static/css/input.css -o static/css/styles.css --minify

FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN addgroup --system app && adduser --system --ingroup app app

COPY --from=builder /usr/local /usr/local

COPY --from=builder --chown=app:app /app/alembic ./alembic
COPY --from=builder --chown=app:app /app/alembic.ini ./alembic.ini
COPY --from=builder --chown=app:app /app/app ./app
COPY --from=builder --chown=app:app /app/gunicorn.conf.py ./gunicorn.conf.py
COPY --from=builder --chown=app:app /app/pyproject.toml ./pyproject.toml
COPY --from=builder --chown=app:app /app/static ./static
COPY --from=builder --chown=app:app /app/templates ./templates

RUN chown -R app:app /app
USER app

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=3).read()"

CMD ["gunicorn", "-c", "gunicorn.conf.py", "app.main:app"]
