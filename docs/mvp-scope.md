# Tinder MVP — Scope & Acceptance Contract

## Stack

- **Runtime:** Python 3.12, FastAPI, uvicorn
- **Datastore:** PostgreSQL (with geohash helper)
- **Cache:** Redis (candidate feed, swiped-ID bloom filter)
- **Tests:** pytest + httpx (ASGITransport for functional)
- **Deploy:** Docker Compose (app + postgres + redis)
- **Port:** `${APP_PORT:-8020}:8000`

## Scope IN

- Profile creation and editing (name, gender, age, bio, photos as URLs, location as lat/lon)
- Discovery preferences (gender, age range, distance radius stored on profile)
- Feed: GET nearby candidates filtered by preferences, excluding previously-swiped profiles
- Swipe: record like/pass, detect mutual matches synchronously
- Match list with last message preview
- Basic messaging between matched users (send, paginated history)
- Unmatch (soft-delete match)

## Scope OUT

- WebSocket / real-time push notifications (polling only for MVP)
- Cassandra / geo-distributed deployment (single Postgres)
- CDN signed-URL photo upload (photos are URL strings)
- Recommendation ranking / ELO scoring (chronological + distance sort for MVP)
- Redis Stack Bloom filter (use a Redis Set for swiped-ID tracking — simpler, exact)
- Photo moderation / NSFW detection
- Subscription tiers, Passport, Boost, Super Like
- Social-auth account linking
- Analytics / A/B testing platform

## Functional Requirements

**FR-1 — Create/edit profile.** `POST /v1/profile/me` creates (or upserts on repeat call with same user) a profile with name, gender (men/women/everyone), age, bio, photos (list of URL strings, max 9), and lat/lon. Returns 201 with the profile. Minimum age 18 enforced.

**FR-2 — Set discovery preferences.** `POST /v1/profile/me` includes optional `preferences` field: `{gender, age_min, age_max, radius_km}`. Radius clamped 1–160 km. Takes effect on next feed request.

**FR-3 — Feed.** `GET /v1/feed?lat=&lon=` returns up to 50 candidate profiles (user_id, name, age, photos[0], distance_km) sorted by distance. Excludes profiles matching the user's own gender preference, age range, distance radius, and any profile the user has previously swiped on.

**FR-4 — Swipe.** `POST /v1/swipe {swiped_id, decision}` where decision ∈ {like, pass}. Returns `{is_match: bool, match_id: string|null}`. If this is a mutual like (swiped user previously liked the swiper), creates a match and returns `is_match: true` with the match_id. Swiping the same profile twice is idempotent (returns existing swipe result). Swiping on a matched user returns 409.

**FR-5 — Match list.** `GET /v1/matches` returns paginated list of active matches with `{match_id, other_user: {id, name, photos[0]}, last_message_at, preview_text}`.

**FR-6 — Messaging.** `POST /v1/messages/{match_id} {text}` sends a message (sender must be a match participant, match must be active). `GET /v1/messages/{match_id}?before=<message_id>` returns cursor-paginated history (20 per page, reverse chronological).

**FR-7 — Unmatch.** `DELETE /v1/matches/{match_id}` soft-deletes the match (is_active=false). Requesting user must be a participant. Returns 200 with `{unmatched: true}`.

**FR-8 — Health.** `GET /healthz` returns `{"status": "ok"}`.

## Acceptance Criteria (one executable case per FR)

| FR | Test | Assertion |
|---|---|---|
| FR-1 | `POST /v1/profile/me` with valid data | → 201, profile returned with all fields |
| FR-1 | `POST /v1/profile/me` with age < 18 | → 422 |
| FR-2 | `POST /v1/profile/me` with preferences | → 201, preferences stored and returned |
| FR-3 | `GET /v1/feed?lat=40.71&lon=-74.00` for a user | → 200, list of profiles, each with distance_km, filtered by preferences |
| FR-4 | `POST /v1/swipe {swiped_id: B, decision: "like"}` (B hasn't swiped on A) | → 200, `{is_match: false, match_id: null}` |
| FR-4 | After A likes B, B likes A back | → 200, `{is_match: true, match_id: "..."}` |
| FR-4 | Swipe on already-swiped profile | → 200, idempotent (same result as first swipe) |
| FR-4 | Swipe on already-matched user | → 409 |
| FR-5 | `GET /v1/matches` after match formed | → 200, paginated list includes the new match |
| FR-6 | `POST /v1/messages/{match_id} {text: "hey"}` | → 201, message returned with id and timestamp |
| FR-6 | `GET /v1/messages/{match_id}` | → 200, paginated messages, newest first |
| FR-6 | Non-participant sends message | → 403 |
| FR-7 | `DELETE /v1/matches/{match_id}` | → 200, `{unmatched: true}`, match no longer in GET /v1/matches |
| FR-7 | Non-participant unmatches | → 403 |
| FR-8 | `GET /healthz` | → 200, `{"status": "ok"}` |

## Build Plan

See KICKOFF.md chain: architect → senior-engineer → staff-engineer → verifier → sre → writer. The architect writes the executable `verify/acceptance/` suite (one black-box case per FR above). The staff-engineer implements until all pass. The verifier gates. The sre adds compose + CI/CD. The writer produces README + DESIGN.
