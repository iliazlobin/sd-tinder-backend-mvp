"""FR-4: Swipe.

POST /v1/swipe {swiped_id, decision} records a swipe.
Mutual like → match created.
Idempotent on re-swipe. 409 on already-matched.
"""

from verify.acceptance.conftest import (
    assert_json_200,
    assert_409,
    assert_422,
    create_profile,
)


def test_swipe_like_no_match(client):
    """Like on a user who hasn't liked back → {is_match: false, match_id: null}."""
    user_a = "swipe-a-000000000000000000001"
    user_b = "swipe-b-000000000000000000001"

    create_profile(client, user_a, name="Alice", gender="women", lat=40.71, lon=-74.00)
    create_profile(client, user_b, name="Bob", gender="men", lat=40.71, lon=-74.00)

    body = assert_json_200(
        client.post(
            "/v1/swipe",
            json={"swiped_id": user_b, "decision": "like"},
            headers={"X-User-Id": user_a},
        )
    )
    assert body["is_match"] is False
    assert body["match_id"] is None


def test_swipe_pass_no_match(client):
    """Pass on a user → {is_match: false, match_id: null}."""
    user_a = "swipe-pass-a-0000000000000001"
    user_b = "swipe-pass-b-0000000000000001"

    create_profile(client, user_a, name="Alice", gender="women", lat=40.71, lon=-74.00)
    create_profile(client, user_b, name="Bob", gender="men", lat=40.71, lon=-74.00)

    body = assert_json_200(
        client.post(
            "/v1/swipe",
            json={"swiped_id": user_b, "decision": "pass"},
            headers={"X-User-Id": user_a},
        )
    )
    assert body["is_match"] is False
    assert body["match_id"] is None


def test_mutual_like_creates_match(client):
    """Alice likes Bob, then Bob likes Alice back → match created."""
    user_a = "swipe-mutual-a-00000000000001"
    user_b = "swipe-mutual-b-00000000000001"

    create_profile(client, user_a, name="Alice", gender="women", lat=40.71, lon=-74.00)
    create_profile(client, user_b, name="Bob", gender="men", lat=40.71, lon=-74.00)

    # Alice likes Bob
    a_body = assert_json_200(
        client.post(
            "/v1/swipe",
            json={"swiped_id": user_b, "decision": "like"},
            headers={"X-User-Id": user_a},
        )
    )
    assert a_body["is_match"] is False

    # Bob likes Alice back → match!
    b_body = assert_json_200(
        client.post(
            "/v1/swipe",
            json={"swiped_id": user_a, "decision": "like"},
            headers={"X-User-Id": user_b},
        )
    )
    assert b_body["is_match"] is True, f"Expected match, got {b_body}"
    assert b_body["match_id"] is not None
    assert len(b_body["match_id"]) > 0


def test_swipe_idempotent(client):
    """Swiping same profile twice returns same result."""
    user_a = "swipe-idem-a-0000000000000001"
    user_b = "swipe-idem-b-0000000000000001"

    create_profile(client, user_a, name="Alice", gender="women", lat=40.71, lon=-74.00)
    create_profile(client, user_b, name="Bob", gender="men", lat=40.71, lon=-74.00)

    r1 = assert_json_200(
        client.post(
            "/v1/swipe",
            json={"swiped_id": user_b, "decision": "like"},
            headers={"X-User-Id": user_a},
        )
    )
    r2 = assert_json_200(
        client.post(
            "/v1/swipe",
            json={"swiped_id": user_b, "decision": "like"},
            headers={"X-User-Id": user_a},
        )
    )
    assert r1["is_match"] == r2["is_match"]
    assert r1["match_id"] == r2["match_id"]


def test_swipe_self_rejected(client):
    """Swiping on yourself → 422."""
    user_id = "swipe-self-0000000000000000001"
    create_profile(client, user_id, name="Self", gender="men", lat=40.71, lon=-74.00)

    r = client.post(
        "/v1/swipe",
        json={"swiped_id": user_id, "decision": "like"},
        headers={"X-User-Id": user_id},
    )
    assert_422(r)


def test_swipe_already_matched_returns_409(client):
    """Swiping on a user you've already matched with → 409."""
    user_a = "swipe-409-a-000000000000000001"
    user_b = "swipe-409-b-000000000000000001"

    create_profile(client, user_a, name="Alice", gender="women", lat=40.71, lon=-74.00)
    create_profile(client, user_b, name="Bob", gender="men", lat=40.71, lon=-74.00)

    # Mutual like creates match
    client.post(
        "/v1/swipe",
        json={"swiped_id": user_b, "decision": "like"},
        headers={"X-User-Id": user_a},
    )
    client.post(
        "/v1/swipe",
        json={"swiped_id": user_a, "decision": "like"},
        headers={"X-User-Id": user_b},
    )

    # Now try swiping again on matched user
    r = client.post(
        "/v1/swipe",
        json={"swiped_id": user_b, "decision": "like"},
        headers={"X-User-Id": user_a},
    )
    assert_409(r)


def test_swipe_pass_then_like_replaces(client):
    """Pass then like on same user: idempotent or replaced. MVP spec says
    idempotent returns first result. But re-swiping from pass to like
    is undefined — this test documents the behavior."""
    user_a = "swipe-undo-a-00000000000000001"
    user_b = "swipe-undo-b-00000000000000001"

    create_profile(client, user_a, name="Alice", gender="women", lat=40.71, lon=-74.00)
    create_profile(client, user_b, name="Bob", gender="men", lat=40.71, lon=-74.00)

    # Pass first
    assert_json_200(
        client.post(
            "/v1/swipe",
            json={"swiped_id": user_b, "decision": "pass"},
            headers={"X-User-Id": user_a},
        )
    )

    # Then like (idempotent → returns pass result, or may update)
    r2 = client.post(
        "/v1/swipe",
        json={"swiped_id": user_b, "decision": "like"},
        headers={"X-User-Id": user_a},
    )
    # System may return 200 (idempotent = pass result) or 200 (updated decision)
    assert r2.status_code in (
        200,
        409,
    ), f"Expected 200 or 409, got {r2.status_code}: {r2.text}"
