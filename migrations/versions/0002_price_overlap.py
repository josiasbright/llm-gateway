from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute(
        """
        ALTER TABLE model_prices ADD CONSTRAINT model_prices_no_overlap
            EXCLUDE USING gist (
                provider WITH =,
                model WITH =,
                tstzrange(valid_from, valid_to) WITH &&
            )
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE model_prices DROP CONSTRAINT IF EXISTS model_prices_no_overlap")
    op.execute("DROP EXTENSION IF EXISTS btree_gist")
