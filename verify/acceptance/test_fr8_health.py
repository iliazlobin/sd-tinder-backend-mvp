"""FR-8: Health.

GET /healthz → 200 {"status": "ok"}.
"""

from verify.acceptance.conftest import assert_json_200


def test_health_check(client):
    """GET /healthz returns 200 with {"status": "ok"}."""
    body = assert_json_200(client.get("/healthz"))
    assert body == {"status": "ok"}, f"Expected {{'status': 'ok'}}, got {body}"
