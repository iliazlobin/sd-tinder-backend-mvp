# Multi-stage build for Tinder MVP.
# Stage 1 installs the app + deps into a self-contained virtualenv at /opt/venv;
# stage 2 copies that venv into a slim runtime. Installing into a venv (rather than
# `pip install --target` + copying site-packages) preserves the console-entry-point
# scripts (uvicorn, alembic, ...) on PATH — copying only site-packages drops them,
# and a follow-up `pip install .` sees deps already satisfied and never regenerates
# them, so `uvicorn`/`alembic` end up unresolvable in the container.

# Stage 1: build into a venv
FROM python:3.12-slim AS builder

ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /app

RUN python -m venv /opt/venv && \
    pip install --no-cache-dir --upgrade pip setuptools wheel

COPY pyproject.toml README.md ./
COPY src/ src/
RUN pip install --no-cache-dir .

# Stage 2: runtime — slim image with the prebuilt venv
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"
WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY src/ src/
COPY pyproject.toml alembic.ini ./
COPY alembic/ alembic/

EXPOSE 8000

HEALTHCHECK --interval=5s --timeout=3s --retries=10 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz')"

CMD ["uvicorn", "tinder.main:app", "--host", "0.0.0.0", "--port", "8000"]
