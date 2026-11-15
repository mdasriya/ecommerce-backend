"""create categories table

BASELINE migration. It describes the `categories` table exactly as it already
existed in the database before Alembic was introduced (it was created by
Base.metadata.create_all). Existing databases are marked as being at this
revision with `alembic stamp 0001` (no SQL executed); brand-new databases
(a new Neon branch, the test database, production) create it normally.

Revision ID: 0001
Revises:
Create Date: 2026-11-14 21:59:02.425739

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("slug", sa.String(length=180), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("banner_image_url", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("show_in_menu", sa.Boolean(), nullable=False),
        sa.Column("is_featured", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="categories_pkey"),
        sa.ForeignKeyConstraint(
            ["parent_id"], ["categories.id"], name="categories_parent_id_fkey"
        ),
    )
    op.create_index("ix_categories_slug", "categories", ["slug"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_categories_slug", table_name="categories")
    op.drop_table("categories")
