"""FR-7: Unmatch.

DELETE /v1/matches/{match_id} → 200 {unmatched: true} (soft delete).
Match no longer in GET /v1/matches.
Non-participant → 403.
"""

from verify.acceptance.conftest import (
    assert_json_200,
    assert_403,
    assert_404,
    create_profile,
)


def _create_match(client, user_a, user_b):
    """Helper: create two profiles, mutual like, return match_id."""
    create_profile(client, user_a, name="Alice", gender="women", lat=40.71, lon=-74.00)
    create_profile(client, user_b, name="Bob", gender="men", lat=40.71, lon=-74.00)

    client.post(
        "/v1/swipe",
        json={"swiped_id": user_b, "decision": "like"},
        headers={"X-User-Id": user_a},
    )
    resp = assert_json_200(
        client.post(
            "/v1/swipe",
            json={"swiped_id": user_a, "decision": "like"},
            headers={"X-User-Id": user_b},
        )
    )
    assert resp["is_match"] is True
    return resp["match_id"]


def test_unmatch_success(client):
    """DELETE /v1/matches/{match_id} → 200 {unmatched: true}."""
    user_a = "unmatch-a-00000000000000000001"
    user_b = "unmatch-b-00000000000000000001"
    match_id = _create_match(client, user_a, user_b)

    body = assert_json_200(
        client.delete(
            f"/v1/matches/{match_id}",
            headers={"X-User-Id": user_a},
        )
    )
    assert body["unmatched"] is True


def test_unmatch_removes_from_match_list(client):
    """After unmatch, GET /v1/matches no longer includes the match."""
    user_a = "unmatch-list-a-000000000000001"
    user_b = "unmatch-list-b-000000000000001"
    match_id = _create_match(client, user_a, user_b)

    # Verify match exists
    body_before = assert_json_200(
        client.get("/v1/matches", headers={"X-User-Id": user_a})
    )
    match_ids_before = [m["match_id"] for m in body_before["matches"]]
    assert match_id in match_ids_before

    # Unmatch
    assert_json_200(
        client.delete(
            f"/v1/matches/{match_id}",
            headers={"X-User-Id": user_a},
        )
    )

    # Verify gone
    body_after = assert_json_200(
        client.get("/v1/matches", headers={"X-User-Id": user_a})
    )
    match_ids_after = [m["match_id"] for m in body_after["matches"]]
    assert match_id not in match_ids_after, \
        f"Match {match_id} should not appear after unmatch"


def test_either_participant_can_unmatch(client):
    """Both user_a and user_b can unmatch."""
    user_a = "unmatch-either-a-0000000000001"
    user_b = "unmatch-either-b-0000000000001"
    match_id = _create_match(client, user_a, user_b)

    # User B unmatches
    body = assert_json_200(
        client.delete(
            f"/v1/matches/{match_id}",
            headers={"X-User-Id": user_b},
        )
    )
    assert body["unmatched"] is True


def test_unmatch_idempotent(client):
    """Double unmatch → 404 or 200 (already unmatched)."""
    user_a = "unmatch-idem-a-00000000000001"
    user_b = "unmatch-idem-b-00000000000001"
    match_id = _create_match(client, user_a, user_b)

    # First unmatch
    assert_json_200(
        client.delete(
            f"/v1/matches/{match_id}",
            headers={"X-User-Id": user_a},
        )
    )

    # Second unmatch — 200 (idempotent) or 404
    r = client.delete(
        f"/v1/matches/{match_id}",
        headers={"X-User-Id": user_a},
    )
    assert r.status_code in (200, 404), \
        f"Expected 200 or 404 on double unmatch, got {r.status_code}: {r.text}"


def test_non_participant_cannot_unmatch(client):
    """Non-participant DELETE → 403."""
    user_a = "unmatch-deny-a-00000000000001"
    user_b = "unmatch-deny-b-00000000000001"
    outsider = "unmatch-deny-c-00000000000001"
    match_id = _create_match(client, user_a, user_b)

    create_profile(client, outsider, name="Outsider", gender="men", lat=40.71, lon=-74.00)

    r = client.delete(
        f"/v1/matches/{match_id}",
        headers={"X-User-Id": outsider},
    )
    assert_403(r)


def test_unmatch_nonexistent_match_returns_404(client):
    """DELETE on non-existent match_id → 404."""
    create_profile(
        client, "unmatch-404-user-000000000001",
        name="Loner", gender="women", lat=40.71, lon=-74.00,
    )
    r = client.delete(
        "/v1/matches/nonexistent-match-id-0000",
        headers={"X-User-Id": "unmatch-404-user-000000000001"},
    )
    assert_404(r)
