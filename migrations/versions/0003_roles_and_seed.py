from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ROLES = ("gateway_app", "gateway_purge")

APP_TABLES = (
    "workspaces",
    "projects",
    "agents",
    "api_keys",
    "provider_credentials",
    "model_prices",
    "budgets",
    "budget_counters",
    "alerts",
    "admin_sessions",
)
PURGE_TABLES = ("usage_events", "alerts", "api_keys", "admin_sessions")


def upgrade() -> None:
    for role in ROLES:
        op.execute(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{role}') THEN
                    CREATE ROLE {role} NOLOGIN;
                END IF;
            END
            $$
            """
        )
    for table in APP_TABLES:
        op.execute(f"GRANT SELECT, INSERT, UPDATE ON {table} TO gateway_app")
    op.execute("GRANT SELECT, INSERT ON usage_events TO gateway_app")
    for table in PURGE_TABLES:
        op.execute(f"GRANT SELECT, DELETE ON {table} TO gateway_purge")

    op.execute("INSERT INTO workspaces (id, name) VALUES (gen_random_uuid(), 'default')")
    op.execute(
        """
        INSERT INTO model_prices
            (id, provider, model, price_in_micro_per_mtok, price_out_micro_per_mtok, valid_from)
        VALUES
            (gen_random_uuid(), 'mock', 'mock-small', 1000000, 2000000, '2000-01-01+00'),
            (gen_random_uuid(), 'mock', 'mock-large', 3000000, 6000000, '2000-01-01+00')
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM model_prices WHERE provider = 'mock'")
    op.execute("DELETE FROM workspaces WHERE name = 'default'")
    for table in APP_TABLES + ("usage_events",):
        op.execute(f"REVOKE ALL ON {table} FROM gateway_app")
    for table in PURGE_TABLES:
        op.execute(f"REVOKE ALL ON {table} FROM gateway_purge")
