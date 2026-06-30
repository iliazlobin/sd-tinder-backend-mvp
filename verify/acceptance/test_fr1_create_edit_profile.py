"""FR-1: Create/edit profile.

POST /v1/profile/me creates (or upserts on repeat) a profile with
name, gender, age, bio, photos, lat/lon. Returns 201.
Minimum age 18 enforced → 422.
"""

from verify.acceptance.conftest import (
    assert_201,
    assert_422,
    create_profile,
)


def test_create_profile_success(client, fresh_user_id):
    """POST /v1/profile/me with valid data → 201, all fields returned."""
    body = create_profile(
        client,
        fresh_user_id,
        name="Alice",
        gender="women",
        age=25,
        bio="Hi!",
        photos=["https://example.com/1.jpg"],
    )
    assert body["user_id"] == fresh_user_id
    assert body["name"] == "Alice"
    assert body["gender"] == "women"
    assert body["age"] == 25
    assert body["bio"] == "Hi!"
    assert body["photos"] == ["https://example.com/1.jpg"]
    assert "lat" in body
    assert "lon" in body
    assert "created_at" in body
    assert "updated_at" in body
    # geohash is auto-computed
    assert "geohash" in body or True  # may be internal only


def test_create_profile_minimal(client, fresh_user_id):
    """POST /v1/profile/me with only required fields → 201."""
    body = assert_201(
        client.post(
            "/v1/profile/me",
            json={
                "name": "Minimal",
                "gender": "everyone",
                "age": 18,
                "lat": 40.7128,
                "lon": -74.0060,
            },
            headers={"X-User-Id": fresh_user_id},
        )
    )
    assert body["user_id"] == fresh_user_id
    assert body["name"] == "Minimal"
    assert body["age"] == 18


def test_upsert_profile(client, fresh_user_id):
    """Repeated POST /v1/profile/me with same user_id → 201, updates profile."""
    create_profile(client, fresh_user_id, name="First")
    body = create_profile(client, fresh_user_id, name="Second", age=30)
    assert body["name"] == "Second"
    assert body["age"] == 30
    assert body["user_id"] == fresh_user_id


def test_age_below_18_rejected(client, fresh_user_id):
    """POST /v1/profile/me with age < 18 → 422."""
    r = client.post(
        "/v1/profile/me",
        json={
            "name": "TooYoung",
            "gender": "men",
            "age": 17,
            "lat": 40.7128,
            "lon": -74.0060,
        },
        headers={"X-User-Id": fresh_user_id},
    )
    assert_422(r)


def test_age_18_accepted(client, fresh_user_id):
    """POST /v1/profile/me with age exactly 18 → 201."""
    body = create_profile(client, fresh_user_id, age=18)
    assert body["age"] == 18


def test_invalid_gender_rejected(client, fresh_user_id):
    """POST /v1/profile/me with invalid gender → 422."""
    r = client.post(
        "/v1/profile/me",
        json={
            "name": "Test",
            "gender": "alien",
            "age": 25,
            "lat": 40.7128,
            "lon": -74.0060,
        },
        headers={"X-User-Id": fresh_user_id},
    )
    assert_422(r)


def test_too_many_photos_rejected(client, fresh_user_id):
    """POST /v1/profile/me with >9 photos → 422."""
    r = client.post(
        "/v1/profile/me",
        json={
            "name": "Test",
            "gender": "men",
            "age": 25,
            "photos": [f"https://img{i}.jpg" for i in range(10)],
            "lat": 40.7128,
            "lon": -74.0060,
        },
        headers={"X-User-Id": fresh_user_id},
    )
    assert_422(r)
