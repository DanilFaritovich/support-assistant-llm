"""Create bounded guest workspace settings storage.

Revision ID: 9d5f41a8c201
Revises: 6875848d7404
"""

import sqlalchemy as sa
from alembic import op

revision = "9d5f41a8c201"
down_revision = "6875848d7404"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "guest_workspaces",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("data", sa.Text(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.Integer(), nullable=False),
    )
    op.create_index(
        "ix_guest_workspaces_expires_at", "guest_workspaces", ["expires_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_guest_workspaces_expires_at", table_name="guest_workspaces")
    op.drop_table("guest_workspaces")
