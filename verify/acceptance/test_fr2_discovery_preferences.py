"""FR-2: Set discovery preferences.

POST /v1/profile/me with optional `preferences` field:
{gender, age_min, age_max, radius_km}.
Radius clamped 1–160 km. Stored and returned.
"""

from verify.acceptance.conftest import (
    create_profile,
)


def test_set_preferences_stored_and_returned(client, fresh_user_id):
    """POST with preferences → 201, preferences in response body."""
    body = create_profile(
        client,
        fresh_user_id,
        preferences={
            "gender": "women",
            "age_min": 22,
            "age_max": 35,
            "radius_km": 25,
        },
    )
    assert body["preferences"] == {
        "gender": "women",
        "age_min": 22,
        "age_max": 35,
        "radius_km": 25,
    }


def test_preferences_optional(client, fresh_user_id):
    """POST without preferences → 201, preferences default or empty."""
    body = create_profile(client, fresh_user_id)
    # Preferences may be null, empty dict, or absent
    prefs = body.get("preferences", {})
    assert prefs is None or isinstance(prefs, dict), \
        f"preferences should be null or dict, got {type(prefs)}"


def test_radius_clamped_at_1(client, fresh_user_id):
    """Radius below 1 → clamped to 1 or 422. MVP design says clamp 1-160."""
    r = client.post(
        "/v1/profile/me",
        json={
            "name": "Test",
            "gender": "men",
            "age": 25,
            "lat": 40.7128,
            "lon": -74.0060,
            "preferences": {"gender": "women", "age_min": 22, "age_max": 35, "radius_km": 0},
        },
        headers={"X-User-Id": fresh_user_id},
    )
    # Clamped: 0 → 1 (returns 201 with radius_km=1).
    # If system rejects instead, that's also valid (422).
    if r.status_code == 201:
        body = r.json()
        assert body["preferences"]["radius_km"] == 1, \
            f"Expected radius_km=1 after clamp, got {body['preferences']['radius_km']}"
    elif r.status_code == 422:
        pass  # rejection is also acceptable
    else:
        assert False, f"Unexpected status {r.status_code}: {r.text}"


def test_radius_clamped_at_160(client, fresh_user_id):
    """Radius above 160 → clamped to 160 or 422."""
    r = client.post(
        "/v1/profile/me",
        json={
            "name": "Test",
            "gender": "men",
            "age": 25,
            "lat": 40.7128,
            "lon": -74.0060,
            "preferences": {"gender": "women", "age_min": 22, "age_max": 35, "radius_km": 500},
        },
        headers={"X-User-Id": fresh_user_id},
    )
    if r.status_code == 201:
        body = r.json()
        assert body["preferences"]["radius_km"] == 160, \
            f"Expected radius_km=160 after clamp, got {body['preferences']['radius_km']}"
    elif r.status_code == 422:
        pass
    else:
        assert False, f"Unexpected status {r.status_code}: {r.text}"


def test_update_preferences(client, fresh_user_id):
    """Update preferences on a subsequent POST → takes effect."""
    create_profile(
        client,
        fresh_user_id,
        preferences={"gender": "men", "age_min": 20, "age_max": 30, "radius_km": 10},
    )
    body = create_profile(
        client,
        fresh_user_id,
        preferences={"gender": "women", "age_min": 25, "age_max": 40, "radius_km": 50},
    )
    assert body["preferences"]["gender"] == "women"
    assert body["preferences"]["radius_km"] == 50
