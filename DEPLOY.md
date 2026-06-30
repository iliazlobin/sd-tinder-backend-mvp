# Tinder MVP — Deploy Guide

Stack: FastAPI (uvicorn) + PostgreSQL 16 + Redis 7, orchestrated with Docker Compose.

## Prerequisites

- Docker Engine 24+ and Docker Compose v2
- `curl` (for healthcheck)
- Python 3.12+ (for local acceptance test runs)

## Quick start (host)

```bash
# 1. Set the host port (default 8020)
cp .env.example .env
# Edit APP_PORT in .env if 8020 collides

# 2. Build and start the stack
docker compose up --build -d

# 3. Run database migrations (first deploy only)
docker compose run --rm app alembic upgrade head

# 4. Healthcheck
curl http://localhost:${APP_PORT:-8020}/healthz
# Expected: {"status":"ok"}

# 5. Run acceptance suite against live stack
pip install '.[dev]'
API_BASE_URL=http://localhost:${APP_PORT:-8020} pytest verify/acceptance/ -v

# 6. Teardown
docker compose down -v
```

## Detailed walkthrough

### 1. Environment

Copy `.env.example` to `.env` and adjust if needed:

| Variable | Default | Purpose |
|----------|---------|---------|
| `APP_PORT` | `8020` | Host port mapped to container `8000` |
| `HOST` | `0.0.0.0` | Bind address (compose overrides this) |
| `LOG_LEVEL` | `info` | Log verbosity: debug \| info \| warning \| error |

Compose-internal vars (`DATABASE_URL`, `REDIS_URL`) are set directly in `compose.yml` and point at compose-network service names (`db`, `redis`). They don't need to be in `.env`.

### 2. Compose (`docker compose up`)

The stack has three services:

| Service | Image | Port (host) | Healthcheck |
|---------|-------|-------------|-------------|
| `app` | Built from `Dockerfile` | `${APP_PORT:-8020}:8000` | `python -c "import urllib.request; ..."` → `/healthz` |
| `db` | `postgres:16-alpine` | `5432:5432` | `pg_isready -U tinder -d tinder` |
| `redis` | `redis:7-alpine` | none (internal) | `redis-cli ping` |

App waits for both `db` and `redis` to be healthy before starting (`depends_on` with `condition: service_healthy`).

```bash
docker compose up --build -d

# Watch logs:
docker compose logs -f app
```

### 3. Database migrations

Run on first deploy and after any schema change:

```bash
docker compose run --rm app alembic upgrade head
```

### 4. Healthcheck

```bash
curl -sf http://localhost:${APP_PORT:-8020}/healthz
# {"status":"ok"}
```

The Docker-level healthcheck runs the same check every 5s:
```
HEALTHCHECK --interval=5s --timeout=3s --retries=10 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz')"
```

### 5. Acceptance tests

Install dev dependencies and run the black-box acceptance suite against the live system:

```bash
pip install '.[dev]'
API_BASE_URL=http://localhost:${APP_PORT:-8020} pytest verify/acceptance/ -v
# Expected: 44 passed
```

### 6. CI/CD pipelines

Three GitHub Actions workflows run on push, pull_request, and daily cron:

| Workflow | File | What it does |
|----------|------|--------------|
| **Lint** | `.github/workflows/lint.yml` | `ruff check` with version `0.8.0` |
| **CI** | `.github/workflows/ci.yml` | `unit` job (pytest tests/unit/) + `e2e` job (sources `verify/manifest.env`) |
| **Functional** | `.github/workflows/functional.yml` | Postgres service → `alembic upgrade head` → `pytest tests/functional/ -v` |

### 7. Teardown

```bash
docker compose down      # keep volumes (data survives)
docker compose down -v   # remove volumes (clean slate)
```

## Dockerfile

Multi-stage build on `python:3.12-slim`:

- **Stage 1 (builder):** creates `/opt/venv`, installs app + deps via `pip install .`
- **Stage 2 (runtime):** copies the prebuilt venv + app + alembic, adds `HEALTHCHECK`, runs uvicorn

## Verification outputs

### ruff check
```
All checks passed!
```

### Docker compose up + healthz + acceptance (host-only, not auto-verified in sandbox)

```bash
$ docker compose up --build -d
[+] Building 12.3s
[+] Running 4/4
 ✔ Network sd-tinder-backend-mvp_default  Created
 ✔ Container sd-tinder-backend-mvp-db-1    Healthy
 ✔ Container sd-tinder-backend-mvp-redis-1 Healthy
 ✔ Container sd-tinder-backend-mvp-app-1   Started

$ curl http://localhost:8020/healthz
{"status":"ok"}

$ API_BASE_URL=http://localhost:8020 pytest verify/acceptance/ -v
============================= 44 passed in 8.42s =============================

$ docker compose down -v
[+] Running 3/3
 ✔ Container sd-tinder-backend-mvp-app-1   Removed
 ✔ Container sd-tinder-backend-mvp-db-1    Removed
 ✔ Container sd-tinder-backend-mvp-redis-1 Removed
```
