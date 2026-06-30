"""FR-3: Feed.

GET /v1/feed?lat=&lon= returns up to 50 candidate profiles sorted by distance,
filtered by preferences, excluding previously-swiped profiles.
"""

from verify.acceptance.conftest import (
    create_profile,
)


def test_feed_returns_candidates_sorted_by_distance(client, fresh_user_id):
    """Create users at varying distances, feed returns sorted by distance_km."""
    requester_id = fresh_user_id

    # Create requesting user at NYC
    create_profile(
        client,
        requester_id,
        name="Requester",
        gender="women",
        lat=40.7128,
        lon=-74.0060,
        preferences={"gender": "men", "age_min": 18, "age_max": 99, "radius_km": 100},
    )

    # Create candidates at varying distances from NYC
    # Near: same location
    near_id = "near-user-0000000000000000001"
    create_profile(
        client,
        near_id,
        name="Nearby",
        gender="men",
        age=25,
        lat=40.7128,
        lon=-74.0060,
    )

    # Far: ~10km away
    far_id = "far-user-00000000000000000002"
    create_profile(
        client,
        far_id,
        name="FarAway",
        gender="men",
        age=25,
        lat=40.8000,
        lon=-74.0060,
    )

    # Medium: ~5km away
    mid_id = "mid-user-00000000000000000003"
    create_profile(
        client,
        mid_id,
        name="Middle",
        gender="men",
        age=25,
        lat=40.7578,
        lon=-74.0060,
    )

    r = client.get(
        "/v1/feed",
        params={"lat": 40.7128, "lon": -74.0060},
        headers={"X-User-Id": requester_id},
    )
    assert r.status_code == 200, f"Feed failed: {r.text}"
    body = r.json()
    candidates = body["candidates"]

    assert (
        len(candidates) >= 2
    ), f"Expected at least 2 candidates, got {len(candidates)}"

    # Distances should be non-decreasing
    distances = [c["distance_km"] for c in candidates]
    assert distances == sorted(
        distances
    ), f"Candidates not sorted by distance: {distances}"

    # Each candidate has required fields
    for c in candidates:
        assert "user_id" in c
        assert "name" in c
        assert "age" in c
        assert "photos" in c
        assert "distance_km" in c
        assert isinstance(c["distance_km"], (int, float))


def test_feed_excludes_self(client, fresh_user_id):
    """Feed must not return the requesting user's own profile."""
    requester_id = fresh_user_id
    create_profile(
        client,
        requester_id,
        name="Requester",
        gender="women",
        age=25,
        lat=40.7128,
        lon=-74.0060,
        preferences={"gender": "men", "age_min": 18, "age_max": 99, "radius_km": 100},
    )

    r = client.get(
        "/v1/feed",
        params={"lat": 40.7128, "lon": -74.0060},
        headers={"X-User-Id": requester_id},
    )
    assert r.status_code == 200
    body = r.json()
    candidate_ids = [c["user_id"] for c in body["candidates"]]
    assert (
        requester_id not in candidate_ids
    ), f"Feed should not include own profile, got {candidate_ids}"


def test_feed_respects_gender_preference(client):
    """Feed filters by gender preference."""
    requester_id = "gender-test-user-000000000001"
    create_profile(
        client,
        requester_id,
        name="Requester",
        gender="women",
        age=25,
        lat=40.7128,
        lon=-74.0060,
        preferences={"gender": "men", "age_min": 18, "age_max": 99, "radius_km": 100},
    )

    # Create a man (should appear)
    man_id = "gender-test-man-0000000000001"
    create_profile(
        client,
        man_id,
        name="Man",
        gender="men",
        age=25,
        lat=40.7128,
        lon=-74.0060,
    )

    # Create a woman (should NOT appear — requester wants men)
    woman_id = "gender-test-woman-00000000001"
    create_profile(
        client,
        woman_id,
        name="Woman",
        gender="women",
        age=25,
        lat=40.7128,
        lon=-74.0060,
    )

    r = client.get(
        "/v1/feed",
        params={"lat": 40.7128, "lon": -74.0060},
        headers={"X-User-Id": requester_id},
    )
    assert r.status_code == 200
    body = r.json()
    candidate_ids = [c["user_id"] for c in body["candidates"]]

    assert man_id in candidate_ids, "Man should appear in feed"
    assert (
        woman_id not in candidate_ids
    ), "Woman should NOT appear (gender preference mismatch)"


def test_feed_respects_age_range(client):
    """Feed filters by age preference."""
    requester_id = "age-test-user-00000000000001"
    create_profile(
        client,
        requester_id,
        name="Requester",
        gender="women",
        age=25,
        lat=40.7128,
        lon=-74.0060,
        preferences={"gender": "men", "age_min": 25, "age_max": 30, "radius_km": 100},
    )

    # Age 28 — in range
    valid_id = "age-test-valid-00000000000001"
    create_profile(
        client,
        valid_id,
        name="Valid",
        gender="men",
        age=28,
        lat=40.7128,
        lon=-74.0060,
    )

    # Age 20 — below range
    too_young_id = "age-test-young-00000000000001"
    create_profile(
        client,
        too_young_id,
        name="TooYoung",
        gender="men",
        age=20,
        lat=40.7128,
        lon=-74.0060,
    )

    r = client.get(
        "/v1/feed",
        params={"lat": 40.7128, "lon": -74.0060},
        headers={"X-User-Id": requester_id},
    )
    assert r.status_code == 200
    body = r.json()
    candidate_ids = [c["user_id"] for c in body["candidates"]]

    assert valid_id in candidate_ids, "Age 28 should be in range 25-30"
    assert (
        too_young_id not in candidate_ids
    ), "Age 20 should be excluded from 25-30 range"


def test_feed_empty_when_no_candidates(client, fresh_user_id):
    """Feed returns empty list when no matching candidates."""
    requester_id = fresh_user_id
    create_profile(
        client,
        requester_id,
        name="Lonely",
        gender="women",
        age=25,
        lat=0.0,
        lon=0.0,  # middle of ocean, no neighbors
        preferences={"gender": "men", "age_min": 18, "age_max": 99, "radius_km": 1},
    )

    r = client.get(
        "/v1/feed",
        params={"lat": 0.0, "lon": 0.0},
        headers={"X-User-Id": requester_id},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["candidates"] == [], f"Expected empty feed, got {body['candidates']}"


def test_feed_requires_lat_lon(client, fresh_user_id):
    """GET /v1/feed without lat/lon → 422."""
    r = client.get("/v1/feed", headers={"X-User-Id": fresh_user_id})
    assert r.status_code == 422, f"Expected 422 without lat/lon, got {r.status_code}"
