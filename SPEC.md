# Tinder MVP — Engineering Spec (`prj-v2026.06.30.1`, `bar-v2026.06.26.1`)

## 1. Goal & scope

Build a **backend MVP** for Tinder — a mobile dating app where users create profiles, set discovery preferences, swipe through nearby profiles, match mutually, and message. The MVP implements the core swipe→match→chat loop with PostgreSQL (single-node) and Redis caching, deployable via Docker Compose.

**In scope**
- Profile creation/editing with discovery preferences
- Geo-filtered candidate feed (geohash-based, Redis-cached)
- Swipe (like/pass) with synchronous mutual-match detection
- Match list with last-message preview
- Cursor-paginated messaging between matched users
- Unmatch (soft delete)

**Out of scope**
- WebSocket / real-time push notifications (polling only)
- Cassandra / geo-distributed deployment
- CDN signed-URL photo uploads (photos are URL strings)
- Recommendation ranking / ELO scoring (distance-sorted for MVP)
- Redis Stack Bloom filter (Redis Set for exact swiped-ID tracking)
- Photo moderation, subscription tiers, Passport/Boost/Super Like, social-auth, analytics

## 2. Functional requirements

- **FR-1 — Create/edit profile.** `POST /v1/profile/me` creates/upserts profile (name, gender, age, bio, photos[], lat/lon). Returns 201. Age ≥ 18 enforced → 422.
- **FR-2 — Discovery preferences.** `POST /v1/profile/me` with `preferences: {gender, age_min, age_max, radius_km}`. Clamped 1–160 km. Takes effect on next feed.
- **FR-3 — Feed.** `GET /v1/feed?lat=&lon=` → up to 50 candidates sorted by distance, filtered by preferences, excluding previously-swiped profiles → 200.
- **FR-4 — Swipe.** `POST /v1/swipe {swiped_id, decision}` → `{is_match, match_id}`. Mutual like → match created. Idempotent on re-swipe. 409 on already-matched.
- **FR-5 — Match list.** `GET /v1/matches` → paginated active matches with `{match_id, other_user, last_message_at, preview_text}` → 200.
- **FR-6 — Messaging.** `POST /v1/messages/{match_id} {text}` → 201. `GET /v1/messages/{match_id}?before=<cursor>` → cursor-paginated, 20/page, reverse chrono. 403 for non-participant.
- **FR-7 — Unmatch.** `DELETE /v1/matches/{match_id}` → `{unmatched: true}`, soft delete. 403 for non-participant.
- **FR-8 — Health.** `GET /healthz` → `{"status": "ok"}` → 200.

## 3. Stack & deployment

- **Runtime:** Python 3.12, FastAPI, uvicorn
- **Datastore:** PostgreSQL (async via SQLAlchemy + asyncpg)
- **Cache:** Redis (async redis-py)
- **Tests:** pytest + httpx (ASGITransport for functional)
- **Deploy:** Docker Compose (app + postgres + redis)
- **Port:** `${APP_PORT:-8020}:8000`

Design → [System Design: Tinder](https://app.notion.com/p/System-Design-Tinder-38fd865005a881369b51d507cfba29c6). Board: `projects`.

## 4. Data model

```
User
  user_id: string (PK)             ← ULID
  name: string
  gender: string                   ← 'men' | 'women' | 'everyone'
  age: integer
  bio: string
  photos: string[]                 ← CDN URLs, up to 9
  lat: float
  lon: float
  geohash: string                  ← 7-char geohash, for spatial queries
  preferences: json                ← {gender, age_min, age_max, radius_km}
  created_at: timestamp
  updated_at: timestamp

Swipe
  swiper_id: string (PK, FK→User)
  swiped_id: string (PK, FK→User)
  decision: string                 ← 'like' | 'pass'
  created_at: timestamp

Match
  match_id: string (PK)            ← sorted ULID pair: concat(smaller,larger)
  user_a: string (FK→User)
  user_b: string (FK→User)
  is_active: boolean               ← false on unmatch
  last_message_at: timestamp
  preview_text: string             ← first 100 chars of last message
  created_at: timestamp

Message
  message_id: string (PK)          ← ULID
  match_id: string (FK→Match)
  sender_id: string (FK→User)
  text: string
  created_at: timestamp
```

## 5. API

- `POST /v1/profile/me` — create or update profile
- `GET /v1/feed?lat=…&lon=…` — candidate profiles sorted by distance
- `POST /v1/swipe` — record swipe, detect mutual match
- `GET /v1/matches` — paginated active match list
- `POST /v1/messages/{match_id}` — send message
- `GET /v1/messages/{match_id}?before=<cursor>` — message history
- `DELETE /v1/matches/{match_id}` — unmatch (soft delete)
- `GET /healthz` — health check

## 6. Test scenarios

- **Idempotency:** swiping same profile twice returns same result; profile upsert is idempotent
- **Ordering:** messages returned reverse-chronological, newest first
- **Pagination:** match list and message history support cursor-based pagination
- **Ownership:** only match participants can send messages or unmatch
- **Validation:** age < 18 rejected, radius out of range rejected, duplicate swipe on matched user → 409
- **Cross-entity:** unmatch removes match from list; match creation links swipe + match + notification

## 7. Module layout

```
sd-tinder-backend-mvp/
├── src/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models/
│   │   ├── user.py
│   │   ├── swipe.py
│   │   ├── match.py
│   │   └── message.py
│   ├── schemas/
│   │   ├── profile.py
│   │   ├── feed.py
│   │   ├── swipe.py
│   │   ├── match.py
│   │   └── message.py
│   ├── routers/
│   │   ├── profile.py
│   │   ├── feed.py
│   │   ├── swipe.py
│   │   ├── matches.py
│   │   └── messages.py
│   └── services/
│       ├── profile.py
│       ├── feed.py
│       ├── swipe.py
│       ├── match.py
│       ├── message.py
│       └── geohash.py
├── tests/
│   ├── unit/
│   └── functional/
├── verify/
│   └── acceptance/
├── alembic/
├── compose.yml
├── Dockerfile
├── pyproject.toml
└── SPEC.md
```

## 8. Run

```bash
# Build and start
docker compose up --build -d

# Verify health
curl http://localhost:8020/healthz

# Run tests
pip install -e ".[dev]"
pytest tests/unit/ -v
pytest tests/functional/ -v
pytest verify/acceptance/ -v
```
