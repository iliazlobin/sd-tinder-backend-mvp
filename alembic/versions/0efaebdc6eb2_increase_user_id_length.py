"""increase user_id and related FK lengths

Revision ID: 0efaebdc6eb2
Revises: 33a7bfe3fff4
Create Date: 2026-06-30

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0efaebdc6eb2"
down_revision: Union[str, Sequence[str], None] = "33a7bfe3fff4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop FK constraints first so we can alter columns
    op.drop_constraint("messages_sender_id_fkey", "messages", type_="foreignkey")
    op.drop_constraint("messages_match_id_fkey", "messages", type_="foreignkey")
    op.drop_constraint("swipes_swiper_id_fkey", "swipes", type_="foreignkey")
    op.drop_constraint("swipes_swiped_id_fkey", "swipes", type_="foreignkey")
    op.drop_constraint("matches_user_a_fkey", "matches", type_="foreignkey")
    op.drop_constraint("matches_user_b_fkey", "matches", type_="foreignkey")

    # Drop PKs that need altering
    op.drop_constraint("users_pkey", "users")
    op.drop_constraint("matches_pkey", "matches")
    op.drop_constraint("swipes_pkey", "swipes")
    op.drop_constraint("messages_pkey", "messages")

    # Alter user_id columns
    op.alter_column("users", "user_id", type_=sa.String(64))
    op.alter_column("matches", "user_a", type_=sa.String(64))
    op.alter_column("matches", "user_b", type_=sa.String(64))
    op.alter_column("matches", "match_id", type_=sa.String(128))
    op.alter_column("swipes", "swiper_id", type_=sa.String(64))
    op.alter_column("swipes", "swiped_id", type_=sa.String(64))
    op.alter_column("messages", "sender_id", type_=sa.String(64))
    op.alter_column("messages", "match_id", type_=sa.String(128))
    op.alter_column("messages", "message_id", type_=sa.String(64))

    # Recreate PKs
    op.create_primary_key("users_pkey", "users", ["user_id"])
    op.create_primary_key("matches_pkey", "matches", ["match_id"])
    op.create_primary_key("swipes_pkey", "swipes", ["swiper_id", "swiped_id"])
    op.create_primary_key("messages_pkey", "messages", ["message_id"])

    # Recreate FKs
    op.create_foreign_key(
        "matches_user_a_fkey", "matches", "users", ["user_a"], ["user_id"]
    )
    op.create_foreign_key(
        "matches_user_b_fkey", "matches", "users", ["user_b"], ["user_id"]
    )
    op.create_foreign_key(
        "swipes_swiper_id_fkey", "swipes", "users", ["swiper_id"], ["user_id"]
    )
    op.create_foreign_key(
        "swipes_swiped_id_fkey", "swipes", "users", ["swiped_id"], ["user_id"]
    )
    op.create_foreign_key(
        "messages_match_id_fkey", "messages", "matches", ["match_id"], ["match_id"]
    )
    op.create_foreign_key(
        "messages_sender_id_fkey", "messages", "users", ["sender_id"], ["user_id"]
    )


def downgrade() -> None:
    op.drop_constraint("messages_sender_id_fkey", "messages", type_="foreignkey")
    op.drop_constraint("messages_match_id_fkey", "messages", type_="foreignkey")
    op.drop_constraint("swipes_swiper_id_fkey", "swipes", type_="foreignkey")
    op.drop_constraint("swipes_swiped_id_fkey", "swipes", type_="foreignkey")
    op.drop_constraint("matches_user_a_fkey", "matches", type_="foreignkey")
    op.drop_constraint("matches_user_b_fkey", "matches", type_="foreignkey")

    op.drop_constraint("users_pkey", "users")
    op.drop_constraint("matches_pkey", "matches")
    op.drop_constraint("swipes_pkey", "swipes")
    op.drop_constraint("messages_pkey", "messages")

    op.alter_column("users", "user_id", type_=sa.String(26))
    op.alter_column("matches", "user_a", type_=sa.String(26))
    op.alter_column("matches", "user_b", type_=sa.String(26))
    op.alter_column("matches", "match_id", type_=sa.String(52))
    op.alter_column("swipes", "swiper_id", type_=sa.String(26))
    op.alter_column("swipes", "swiped_id", type_=sa.String(26))
    op.alter_column("messages", "sender_id", type_=sa.String(26))
    op.alter_column("messages", "match_id", type_=sa.String(52))
    op.alter_column("messages", "message_id", type_=sa.String(26))

    op.create_primary_key("users_pkey", "users", ["user_id"])
    op.create_primary_key("matches_pkey", "matches", ["match_id"])
    op.create_primary_key("swipes_pkey", "swipes", ["swiper_id", "swiped_id"])
    op.create_primary_key("messages_pkey", "messages", ["message_id"])

    op.create_foreign_key(
        "matches_user_a_fkey", "matches", "users", ["user_a"], ["user_id"]
    )
    op.create_foreign_key(
        "matches_user_b_fkey", "matches", "users", ["user_b"], ["user_id"]
    )
    op.create_foreign_key(
        "swipes_swiper_id_fkey", "swipes", "users", ["swiper_id"], ["user_id"]
    )
    op.create_foreign_key(
        "swipes_swiped_id_fkey", "swipes", "users", ["swiped_id"], ["user_id"]
    )
    op.create_foreign_key(
        "messages_match_id_fkey", "messages", "matches", ["match_id"], ["match_id"]
    )
    op.create_foreign_key(
        "messages_sender_id_fkey", "messages", "users", ["sender_id"], ["user_id"]
    )
