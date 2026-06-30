"""FR-6: Messaging.

POST /v1/messages/{match_id} {text} → 201 (sender must be participant).
GET /v1/messages/{match_id} → 200, paginated, reverse chronological.
Non-participant → 403.
"""

from verify.acceptance.conftest import (
    assert_201,
    assert_json_200,
    assert_403,
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


def test_send_message_success(client):
    """POST /v1/messages/{match_id} → 201 with message details."""
    user_a = "msg-send-a-0000000000000000001"
    user_b = "msg-send-b-0000000000000000001"
    match_id = _create_match(client, user_a, user_b)

    body = assert_201(
        client.post(
            f"/v1/messages/{match_id}",
            json={"text": "Hey, how's it going?"},
            headers={"X-User-Id": user_a},
        )
    )
    assert body["match_id"] == match_id
    assert body["sender_id"] == user_a
    assert body["text"] == "Hey, how's it going?"
    assert "message_id" in body
    assert "created_at" in body


def test_get_messages_paginated_newest_first(client):
    """GET /v1/messages/{match_id} returns messages newest first, paginated."""
    user_a = "msg-get-a-0000000000000000001"
    user_b = "msg-get-b-0000000000000000001"
    match_id = _create_match(client, user_a, user_b)

    # Send 3 messages
    assert_201(
        client.post(
            f"/v1/messages/{match_id}",
            json={"text": "First"},
            headers={"X-User-Id": user_a},
        )
    )
    assert_201(
        client.post(
            f"/v1/messages/{match_id}",
            json={"text": "Second"},
            headers={"X-User-Id": user_b},
        )
    )
    assert_201(
        client.post(
            f"/v1/messages/{match_id}",
            json={"text": "Third"},
            headers={"X-User-Id": user_a},
        )
    )

    body = assert_json_200(
        client.get(
            f"/v1/messages/{match_id}",
            headers={"X-User-Id": user_a},
        )
    )
    messages = body["messages"]
    assert len(messages) == 3, f"Expected 3 messages, got {len(messages)}"

    # Should be reverse chronological: Third, Second, First
    assert messages[0]["text"] == "Third"
    assert messages[1]["text"] == "Second"
    assert messages[2]["text"] == "First"


def test_get_messages_cursor_pagination(client):
    """GET with before=<cursor> → next page of messages."""
    user_a = "msg-cursor-a-00000000000000001"
    user_b = "msg-cursor-b-00000000000000001"
    match_id = _create_match(client, user_a, user_b)

    # Send 5 messages
    for i in range(5):
        assert_201(
            client.post(
                f"/v1/messages/{match_id}",
                json={"text": f"Msg{i}"},
                headers={"X-User-Id": user_a},
            )
        )

    # Get first page (default 20, so all 5)
    body = assert_json_200(
        client.get(
            f"/v1/messages/{match_id}",
            params={"limit": 3},
            headers={"X-User-Id": user_a},
        )
    )
    assert len(body["messages"]) == 3

    # Get second page using cursor
    if body.get("next_cursor"):
        body2 = assert_json_200(
            client.get(
                f"/v1/messages/{match_id}",
                params={"before": body["next_cursor"], "limit": 3},
                headers={"X-User-Id": user_a},
            )
        )
        assert len(body2["messages"]) == 2
        # No overlap
        page1_texts = {m["text"] for m in body["messages"]}
        page2_texts = {m["text"] for m in body2["messages"]}
        assert page1_texts.isdisjoint(page2_texts)


def test_non_participant_cannot_send_message(client):
    """Non-participant POST → 403."""
    user_a = "msg-nonpart-a-000000000000001"
    user_b = "msg-nonpart-b-000000000000001"
    outsider = "msg-nonpart-c-000000000000001"
    match_id = _create_match(client, user_a, user_b)

    create_profile(
        client, outsider, name="Outsider", gender="men", lat=40.71, lon=-74.00
    )

    r = client.post(
        f"/v1/messages/{match_id}",
        json={"text": "Intruding!"},
        headers={"X-User-Id": outsider},
    )
    assert_403(r)


def test_non_participant_cannot_read_messages(client):
    """Non-participant GET → 403."""
    user_a = "msg-readdeny-a-00000000000001"
    user_b = "msg-readdeny-b-00000000000001"
    outsider = "msg-readdeny-c-00000000000001"
    match_id = _create_match(client, user_a, user_b)

    create_profile(
        client, outsider, name="Outsider", gender="men", lat=40.71, lon=-74.00
    )

    r = client.get(
        f"/v1/messages/{match_id}",
        headers={"X-User-Id": outsider},
    )
    assert_403(r)


def test_both_participants_can_send(client):
    """Both match participants can send messages."""
    user_a = "msg-both-a-000000000000000001"
    user_b = "msg-both-b-000000000000000001"
    match_id = _create_match(client, user_a, user_b)

    a_body = assert_201(
        client.post(
            f"/v1/messages/{match_id}",
            json={"text": "From A"},
            headers={"X-User-Id": user_a},
        )
    )
    assert a_body["sender_id"] == user_a

    b_body = assert_201(
        client.post(
            f"/v1/messages/{match_id}",
            json={"text": "From B"},
            headers={"X-User-Id": user_b},
        )
    )
    assert b_body["sender_id"] == user_b


def test_message_on_inactive_match_rejected(client):
    """Sending message on unmatched (inactive) match → 403 or 404."""
    user_a = "msg-inactive-a-00000000000001"
    user_b = "msg-inactive-b-00000000000001"
    match_id = _create_match(client, user_a, user_b)

    # Unmatch
    assert_json_200(
        client.delete(
            f"/v1/matches/{match_id}",
            headers={"X-User-Id": user_a},
        )
    )

    # Try to send message
    r = client.post(
        f"/v1/messages/{match_id}",
        json={"text": "Still here?"},
        headers={"X-User-Id": user_a},
    )
    assert r.status_code in (
        403,
        404,
    ), f"Expected 403 or 404 on inactive match, got {r.status_code}: {r.text}"
