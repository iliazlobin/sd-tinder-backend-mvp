# Tinder MVP

[![Lint](https://github.com/iliazlobin/sd-tinder-backend-mvp/actions/workflows/lint.yml/badge.svg)](https://github.com/iliazlobin/sd-tinder-backend-mvp/actions/workflows/lint.yml)
[![CI](https://github.com/iliazlobin/sd-tinder-backend-mvp/actions/workflows/ci.yml/badge.svg)](https://github.com/iliazlobin/sd-tinder-backend-mvp/actions/workflows/ci.yml)
[![Functional](https://github.com/iliazlobin/sd-tinder-backend-mvp/actions/workflows/functional.yml/badge.svg)](https://github.com/iliazlobin/sd-tinder-backend-mvp/actions/workflows/functional.yml)

REST polling-based dating-service backend: profiles, geo-filtered discovery feed, swipe/match semantics, match lists, and 1:1 messaging. FastAPI + PostgreSQL 16 + Redis 7, orchestrated with Docker Compose.

## Quick start

```bash
cp .env.example .env                        # adjust APP_PORT if 8020 collides
docker compose up --build -d                # start app + postgres + redis
docker compose run --rm app alembic upgrade head  # first-run migration
curl http://localhost:8020/healthz          # {"status":"ok"}
```

Full deploy walkthrough in [DEPLOY.md](DEPLOY.md).

## API

All endpoints under `/v1`. Requests authenticate via `X-User-Id` header (ULID string). Responses are JSON.

- `POST /v1/profile/me` — create or update profile; returns 201 with full profile. Upserts on repeat calls.
- `GET /v1/profile/me` — read your profile; returns 200.
- `GET /v1/feed?lat=&lon=` — up to 50 candidates sorted by distance, filtered by discovery preferences and excluding already-swiped profiles; returns 200.
- `POST /v1/swipe` — record a like/pass; body: `{"swiped_id", "decision"}`. Returns `{is_match, match_id}`. Mutual like creates a match synchronously.
- `GET /v1/matches` — cursor-paginated list of active matches with `other_user`, `last_message_at`, `preview_text`; returns 200.
- `POST /v1/messages/{match_id}` — send a message; body: `{"text"}`; returns 201. Sender must be a match participant.
- `GET /v1/messages/{match_id}?before=<cursor>` — cursor-paginated message history, 20 per page, reverse chronological; returns 200.
- `DELETE /v1/matches/{match_id}` — unmatch (soft delete, `is_active=false`); returns 200 `{"unmatched":true}`. Caller must be a participant.
- `GET /healthz` — liveness probe; returns 200 `{"status":"ok"}`.

## Configuration

Copy `.env.example` to `.env` and edit:

| Variable | Default | Purpose |
|---|---|---|
| `APP_PORT` | `8020` | Host port mapped to container port `8000` |
| `HOST` | `0.0.0.0` | Bind address |
| `LOG_LEVEL` | `info` | Log verbosity: `debug` | `info` | `warning` | `error` |

Compose-internal vars (`DATABASE_URL`, `REDIS_URL`) are set in `compose.yml` and point at compose-network service names — they do not need to be in `.env`.

## Testing

```bash
pip install '.[dev]'

# White-box tests (unit + functional scenarios)
pytest tests/ -v

# Black-box acceptance suite against a running stack
API_BASE_URL=http://localhost:8020 pytest verify/acceptance/ -v
```

The acceptance suite contains 44 tests — one case per functional requirement assertion — and runs against a live instance over HTTP.

## Architecture

```
Mobile Client → FastAPI (uvicorn, :8000) → PostgreSQL 16 (users, swipes, matches, messages)
                                          → Redis 7 (swiped-ID sets for feed exclusion)
```

**Layering:** `routers/` (HTTP parsing only) → `services/` (business logic + data access) → `models/` (SQLAlchemy ORM) + `schemas/` (Pydantic request/response shapes). No business logic in routers.

**Key decisions:**
- PostgreSQL (single-node): ACID for match consistency. Geohash-based spatial queries via `WHERE geohash LIKE 'prefix%'` for MVP volume.
- Redis Set for swiped-ID tracking: exact membership, zero false positives. `SADD` on swipe, `SMEMBERS` on feed.
- Match detection is synchronous at swipe time: write swipe → check inverse → create match idempotently via sorted ULID pair key.
- HTTP polling only (no WebSockets). Distance-sorted feed (no ELO/ranking). Photos are URL strings (no CDN upload).

## Project layout

```
src/tinder/          FastAPI app — routers → services → models/schemas
alembic/             database migrations (async SQLAlchemy 2.0)
tests/               white-box tests (unit + functional scenarios)
verify/acceptance/   black-box acceptance suite (HTTP against live stack)
compose.yml          app + postgres + redis with healthchecks
Dockerfile           multi-stage build on python:3.12-slim
DEPLOY.md            full deploy walkthrough
```

## Limitations

- Single-node PostgreSQL (vertical scale only; no geo-distribution).
- HTTP polling for match list and messages (no WebSocket push).
- Redis Set for swiped-ID tracking grows linearly with swipe count; migrate to Bloom filter at scale.
- No recommendation ranking / ELO scoring — candidates sorted by Haversine distance.
- Photos stored as URL strings (no signed-URL upload, no CDN, no moderation).
- No OAuth or account service — `user_id` is client-provided (ULID header).
