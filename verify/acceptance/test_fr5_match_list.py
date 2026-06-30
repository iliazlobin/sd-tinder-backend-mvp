"""FR-5: Match list.

GET /v1/matches returns paginated list of active matches with
{match_id, other_user, last_message_at, preview_text}.
"""

from verify.acceptance.conftest import (
    assert_json_200,
    create_profile,
)


def test_match_list_includes_new_match(client):
    """After mutual like creates match, GET /v1/matches includes it."""
    user_a = "matchlist-a-000000000000000001"
    user_b = "matchlist-b-000000000000000001"

    create_profile(client, user_a, name="Alice", gender="women", lat=40.71, lon=-74.00)
    create_profile(client, user_b, name="Bob", gender="men", lat=40.71, lon=-74.00)

    # Mutual like
    client.post(
        "/v1/swipe",
        json={"swiped_id": user_b, "decision": "like"},
        headers={"X-User-Id": user_a},
    )
    swipe_resp = assert_json_200(
        client.post(
            "/v1/swipe",
            json={"swiped_id": user_a, "decision": "like"},
            headers={"X-User-Id": user_b},
        )
    )
    match_id = swipe_resp["match_id"]

    # Check Alice's match list
    body = assert_json_200(
        client.get("/v1/matches", headers={"X-User-Id": user_a})
    )
    matches = body["matches"]
    assert len(matches) >= 1, f"Expected at least 1 match, got {len(matches)}"

    alice_match = next((m for m in matches if m["match_id"] == match_id), None)
    assert alice_match is not None, f"Match {match_id} not in Alice's list"


def test_match_list_other_user_is_correct(client):
    """other_user field shows the non-requesting participant."""
    user_a = "match-other-a-0000000000000001"
    user_b = "match-other-b-0000000000000001"

    create_profile(client, user_a, name="Alice", gender="women", lat=40.71, lon=-74.00)
    create_profile(client, user_b, name="Bob", gender="men", lat=40.71, lon=-74.00)

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

    # From Alice's perspective, other_user should be Bob
    body = assert_json_200(
        client.get("/v1/matches", headers={"X-User-Id": user_a})
    )
    match = body["matches"][0]
    assert match["other_user"]["id"] == user_b
    assert match["other_user"]["name"] == "Bob"

    # From Bob's perspective, other_user should be Alice
    body_b = assert_json_200(
        client.get("/v1/matches", headers={"X-User-Id": user_b})
    )
    match_b = body_b["matches"][0]
    assert match_b["other_user"]["id"] == user_a
    assert match_b["other_user"]["name"] == "Alice"


def test_match_list_pagination(client):
    """Match list supports cursor pagination."""
    # Create requester
    requester = "match-paginate-000000000000001"
    create_profile(
        client, requester,
        name="Requester", gender="women", lat=40.71, lon=-74.00,
    )

    # Create 3 matches
    match_ids = []
    for i in range(3):
        other = f"match-paginate-other-0000000{i}"
        create_profile(
            client, other,
            name=f"Other{i}", gender="men", lat=40.71, lon=-74.00,
        )
        client.post(
            "/v1/swipe",
            json={"swiped_id": other, "decision": "like"},
            headers={"X-User-Id": requester},
        )
        resp = assert_json_200(
            client.post(
                "/v1/swipe",
                json={"swiped_id": requester, "decision": "like"},
                headers={"X-User-Id": other},
            )
        )
        match_ids.append(resp["match_id"])

    # First page
    body = assert_json_200(
        client.get("/v1/matches", params={"limit": 2}, headers={"X-User-Id": requester})
    )
    assert len(body["matches"]) <= 2

    # If there's a next_cursor, fetch second page
    if body.get("next_cursor"):
        body2 = assert_json_200(
            client.get(
                "/v1/matches",
                params={"before": body["next_cursor"], "limit": 2},
                headers={"X-User-Id": requester},
            )
        )
        assert len(body2["matches"]) >= 1
        # No duplicate match_ids across pages
        page1_ids = {m["match_id"] for m in body["matches"]}
        page2_ids = {m["match_id"] for m in body2["matches"]}
        assert page1_ids.isdisjoint(page2_ids), \
            f"Duplicate match_ids across pages: {page1_ids & page2_ids}"


def test_match_list_has_required_fields(client):
    """Each match in list has required fields."""
    user_a = "match-fields-a-0000000000000001"
    user_b = "match-fields-b-0000000000000001"

    create_profile(client, user_a, name="Alice", gender="women", lat=40.71, lon=-74.00)
    create_profile(
        client, user_b, name="Bob", gender="men", lat=40.71, lon=-74.00,
        photos=["https://example.com/bob.jpg"],
    )

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

    body = assert_json_200(
        client.get("/v1/matches", headers={"X-User-Id": user_a})
    )
    match = body["matches"][0]

    assert "match_id" in match
    assert "other_user" in match
    assert "id" in match["other_user"]
    assert "name" in match["other_user"]
    assert "photos" in match["other_user"]
    assert "last_message_at" in match
    assert "preview_text" in match


def test_match_list_empty_for_new_user(client, fresh_user_id):
    """New user with no swipes → empty match list."""
    create_profile(client, fresh_user_id, name="New", gender="women", lat=40.71, lon=-74.00)

    body = assert_json_200(
        client.get("/v1/matches", headers={"X-User-Id": fresh_user_id})
    )
    assert body["matches"] == [], f"Expected empty list, got {body['matches']}"
