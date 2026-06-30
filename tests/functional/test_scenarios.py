"""Functional tests for SPEC SS6 scenarios: idempotency, ordering, pagination, ownership, validation, cross-entity."""

from __future__ import annotations

import pytest


async def _create_match(client, user_a, user_b):
    """Create two profiles and a mutual match. Returns match_id."""
    for uid, name, gender, lat, lon in [
        (user_a, f"UserA-{user_a[:6]}", "women", 40.7128, -74.0060),
        (user_b, f"UserB-{user_b[:6]}", "men", 40.7130, -74.0062),
    ]:
        r = await client.post(
            "/v1/profile/me",
            json={"name": name, "gender": gender, "age": 25, "lat": lat, "lon": lon},
            headers={"X-User-Id": uid},
        )
        assert r.status_code == 201, f"Profile creation failed for {uid}: {r.text}"

    r = await client.post(
        "/v1/swipe",
        json={"swiped_id": user_b, "decision": "like"},
        headers={"X-User-Id": user_a},
    )
    assert r.status_code == 200
    assert r.json()["is_match"] is False

    r = await client.post(
        "/v1/swipe",
        json={"swiped_id": user_a, "decision": "like"},
        headers={"X-User-Id": user_b},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["is_match"] is True
    return data["match_id"]


async def _create_profile(client, user_id):
    r = await client.post(
        "/v1/profile/me",
        json={
            "name": f"User-{user_id[:6]}",
            "gender": "women",
            "age": 25,
            "lat": 40.71,
            "lon": -74.00,
        },
        headers={"X-User-Id": user_id},
    )
    assert r.status_code == 201
    return r.json()


@pytest.mark.asyncio
async def test_profile_upsert_is_idempotent(client):
    user_id = "idem-profile-000000000000000001"
    r1 = await _create_profile(client, user_id)
    assert r1["name"] == f"User-{user_id[:6]}"

    r2 = await client.post(
        "/v1/profile/me",
        json={
            "name": "Alice V2",
            "gender": "women",
            "age": 26,
            "lat": 40.72,
            "lon": -74.01,
        },
        headers={"X-User-Id": user_id},
    )
    assert r2.status_code == 201
    assert r2.json()["name"] == "Alice V2"
    assert r2.json()["age"] == 26
    assert r2.json()["created_at"].replace("Z", "") == r1["created_at"].replace("Z", "")
    assert r2.json()["updated_at"] != r1["updated_at"]


@pytest.mark.asyncio
async def test_swipe_twice_idempotent(client):
    user_a = "idem-swipe-a-00000000000000001"
    user_b = "idem-swipe-b-00000000000000001"
    await _create_profile(client, user_a)
    await _create_profile(client, user_b)

    r1 = await client.post(
        "/v1/swipe",
        json={"swiped_id": user_b, "decision": "like"},
        headers={"X-User-Id": user_a},
    )
    assert r1.status_code == 200
    first = r1.json()

    r2 = await client.post(
        "/v1/swipe",
        json={"swiped_id": user_b, "decision": "like"},
        headers={"X-User-Id": user_a},
    )
    assert r2.status_code == 200
    assert r2.json()["is_match"] == first["is_match"]


@pytest.mark.asyncio
async def test_messages_reverse_chronological(client):
    user_a = "order-msg-a-000000000000000001"
    user_b = "order-msg-b-000000000000000001"
    match_id = await _create_match(client, user_a, user_b)

    for text in ["First", "Second", "Third"]:
        r = await client.post(
            f"/v1/messages/{match_id}",
            json={"text": text},
            headers={"X-User-Id": user_a},
        )
        assert r.status_code == 201

    r = await client.get(f"/v1/messages/{match_id}", headers={"X-User-Id": user_a})
    assert r.status_code == 200
    msgs = r.json()["messages"]
    assert len(msgs) == 3
    assert msgs[0]["text"] == "Third"
    assert msgs[1]["text"] == "Second"
    assert msgs[2]["text"] == "First"


@pytest.mark.asyncio
async def test_message_cursor_pagination(client):
    user_a = "page-msg-a-000000000000000001"
    user_b = "page-msg-b-000000000000000001"
    match_id = await _create_match(client, user_a, user_b)

    for i in range(5):
        r = await client.post(
            f"/v1/messages/{match_id}",
            json={"text": f"Msg{i}"},
            headers={"X-User-Id": user_a},
        )
        assert r.status_code == 201

    r1 = await client.get(
        f"/v1/messages/{match_id}", params={"limit": 3}, headers={"X-User-Id": user_a}
    )
    assert r1.status_code == 200
    b1 = r1.json()
    assert len(b1["messages"]) == 3
    p1_ids = {m["message_id"] for m in b1["messages"]}
    assert b1.get("next_cursor")

    r2 = await client.get(
        f"/v1/messages/{match_id}",
        params={"before": b1["next_cursor"], "limit": 3},
        headers={"X-User-Id": user_a},
    )
    assert r2.status_code == 200
    b2 = r2.json()
    assert len(b2["messages"]) == 2
    p2_ids = {m["message_id"] for m in b2["messages"]}
    assert p1_ids.isdisjoint(p2_ids)


@pytest.mark.asyncio
async def test_match_list_cursor_pagination(client):
    main_user = "match-page-main-000000000000001"
    for i in range(5):
        await _create_match(client, main_user, f"match-page-b-{i:0>20d}")

    r = await client.get(
        "/v1/matches", params={"limit": 3}, headers={"X-User-Id": main_user}
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["matches"]) == 3
    assert body.get("next_cursor") is not None


@pytest.mark.asyncio
async def test_non_participant_cannot_send_message(client):
    user_a = "owner-msg-a-000000000000000001"
    user_b = "owner-msg-b-000000000000000001"
    outsider = "owner-msg-c-000000000000000001"
    match_id = await _create_match(client, user_a, user_b)
    await _create_profile(client, outsider)

    r = await client.post(
        f"/v1/messages/{match_id}", json={"text": "X"}, headers={"X-User-Id": outsider}
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_non_participant_cannot_read_messages(client):
    user_a = "owner-read-a-00000000000000001"
    user_b = "owner-read-b-00000000000000001"
    outsider = "owner-read-c-00000000000000001"
    match_id = await _create_match(client, user_a, user_b)
    await _create_profile(client, outsider)

    r = await client.get(f"/v1/messages/{match_id}", headers={"X-User-Id": outsider})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_non_participant_cannot_unmatch(client):
    user_a = "owner-unmt-a-0000000000000001"
    user_b = "owner-unmt-b-0000000000000001"
    outsider = "owner-unmt-c-0000000000000001"
    match_id = await _create_match(client, user_a, user_b)
    await _create_profile(client, outsider)

    r = await client.delete(f"/v1/matches/{match_id}", headers={"X-User-Id": outsider})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_age_below_18_rejected(client):
    r = await client.post(
        "/v1/profile/me",
        json={
            "name": "TooYoung",
            "gender": "women",
            "age": 17,
            "lat": 40.71,
            "lon": -74.00,
        },
        headers={"X-User-Id": "val-age-000000000000000000001"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_radius_out_of_range_clamped(client):
    r = await client.post(
        "/v1/profile/me",
        json={
            "name": "Wide",
            "gender": "women",
            "age": 25,
            "lat": 40.71,
            "lon": -74.00,
            "preferences": {
                "gender": "everyone",
                "age_min": 18,
                "age_max": 99,
                "radius_km": 200,
            },
        },
        headers={"X-User-Id": "val-radius-00000000000000001"},
    )
    assert r.status_code == 201
    assert r.json()["preferences"]["radius_km"] == 160


@pytest.mark.asyncio
async def test_radius_below_1_clamped(client):
    r = await client.post(
        "/v1/profile/me",
        json={
            "name": "Narrow",
            "gender": "women",
            "age": 25,
            "lat": 40.71,
            "lon": -74.00,
            "preferences": {
                "gender": "everyone",
                "age_min": 18,
                "age_max": 99,
                "radius_km": 0,
            },
        },
        headers={"X-User-Id": "val-radius-lo-00000000000001"},
    )
    assert r.status_code == 201
    assert r.json()["preferences"]["radius_km"] == 1


@pytest.mark.asyncio
async def test_duplicate_swipe_on_matched_returns_409(client):
    user_a = "val-dup-a-000000000000000000001"
    user_b = "val-dup-b-000000000000000000001"
    await _create_match(client, user_a, user_b)

    r = await client.post(
        "/v1/swipe",
        json={"swiped_id": user_b, "decision": "like"},
        headers={"X-User-Id": user_a},
    )
    assert r.status_code == 409
    assert "Already matched" in r.json()["detail"]


@pytest.mark.asyncio
async def test_self_swipe_rejected(client):
    user_id = "val-self-000000000000000000001"
    await _create_profile(client, user_id)

    r = await client.post(
        "/v1/swipe",
        json={"swiped_id": user_id, "decision": "like"},
        headers={"X-User-Id": user_id},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_unmatch_removes_from_list(client):
    user_a = "xent-unmt-a-00000000000000001"
    user_b = "xent-unmt-b-00000000000000001"
    match_id = await _create_match(client, user_a, user_b)

    r1 = await client.get("/v1/matches", headers={"X-User-Id": user_a})
    assert match_id in {m["match_id"] for m in r1.json()["matches"]}

    r2 = await client.delete(f"/v1/matches/{match_id}", headers={"X-User-Id": user_a})
    assert r2.status_code == 200
    assert r2.json()["unmatched"] is True

    r3 = await client.get("/v1/matches", headers={"X-User-Id": user_a})
    assert match_id not in {m["match_id"] for m in r3.json()["matches"]}


@pytest.mark.asyncio
async def test_match_creation_links_swipe_and_match(client):
    user_a = "xent-link-a-00000000000000001"
    user_b = "xent-link-b-00000000000000001"
    await _create_profile(client, user_a)
    await _create_profile(client, user_b)

    r1 = await client.post(
        "/v1/swipe",
        json={"swiped_id": user_b, "decision": "like"},
        headers={"X-User-Id": user_a},
    )
    assert r1.status_code == 200
    assert r1.json()["is_match"] is False

    r2 = await client.post(
        "/v1/swipe",
        json={"swiped_id": user_a, "decision": "like"},
        headers={"X-User-Id": user_b},
    )
    assert r2.status_code == 200
    assert r2.json()["is_match"] is True
    match_id = r2.json()["match_id"]
    assert match_id is not None

    for uid in (user_a, user_b):
        r = await client.get("/v1/matches", headers={"X-User-Id": uid})
        assert match_id in {m["match_id"] for m in r.json()["matches"]}


@pytest.mark.asyncio
async def test_unmatch_is_idempotent(client):
    user_a = "xent-idem-a-00000000000000001"
    user_b = "xent-idem-b-00000000000000001"
    match_id = await _create_match(client, user_a, user_b)

    r1 = await client.delete(f"/v1/matches/{match_id}", headers={"X-User-Id": user_a})
    assert r1.status_code == 200
    assert r1.json()["unmatched"] is True

    r2 = await client.delete(f"/v1/matches/{match_id}", headers={"X-User-Id": user_a})
    assert r2.status_code in (200, 404)
