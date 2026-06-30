"""Unit tests for model imports and configuration."""

from __future__ import annotations



def test_models_import():
    """All model classes should import cleanly."""
    from tinder.models import User, Swipe, Match, Message
    assert User.__tablename__ == "users"
    assert Swipe.__tablename__ == "swipes"
    assert Match.__tablename__ == "matches"
    assert Message.__tablename__ == "messages"


def test_config_defaults():
    """Settings should load with sensible defaults."""
    from tinder.config import Settings
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.host == "0.0.0.0"
    assert s.app_port == 8000
    assert "postgresql" in s.database_url


def test_schemas_import():
    """All schema classes should import cleanly."""
    from tinder.schemas import (
        ProfileCreate,
        SwipeRequest,
        MessageSend,
    )
    # Verify a few key fields
    assert ProfileCreate.model_fields["name"].is_required()
    assert "like" in SwipeRequest.model_fields["decision"].annotation.__args__
    assert MessageSend.model_fields["text"].metadata[0].min_length == 1
