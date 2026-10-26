from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES_DROP_ORDER = (
    "admin_sessions",
    "alerts",
    "budget_counters",
    "budgets",
    "usage_events",
    "model_prices",
    "provider_credentials",
    "api_keys",
    "agents",
    "projects",
    "workspaces",
)


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE workspaces (
            id uuid PRIMARY KEY,
            name text NOT NULL,
            alert_webhook_url text,
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE projects (
            id uuid PRIMARY KEY,
            workspace_id uuid NOT NULL REFERENCES workspaces (id),
            name text NOT NULL CHECK (char_length(name) BETWEEN 1 AND 80),
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (workspace_id, name)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE agents (
            id uuid PRIMARY KEY,
            project_id uuid NOT NULL REFERENCES projects (id),
            name text NOT NULL CHECK (char_length(name) BETWEEN 1 AND 80),
            status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'disabled')),
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (project_id, name)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE api_keys (
            id uuid PRIMARY KEY,
            agent_id uuid NOT NULL REFERENCES agents (id),
            key_prefix text NOT NULL,
            key_hash bytea NOT NULL UNIQUE,
            created_at timestamptz NOT NULL DEFAULT now(),
            last_used_at timestamptz,
            revoked_at timestamptz
        )
        """
    )
    op.execute(
        """
        CREATE TABLE provider_credentials (
            id uuid PRIMARY KEY,
            workspace_id uuid NOT NULL REFERENCES workspaces (id),
            provider text NOT NULL,
            secret_encrypted bytea NOT NULL,
            master_key_id text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (workspace_id, provider)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE model_prices (
            id uuid PRIMARY KEY,
            provider text NOT NULL,
            model text NOT NULL,
            price_in_micro_per_mtok bigint NOT NULL CHECK (price_in_micro_per_mtok >= 0),
            price_out_micro_per_mtok bigint NOT NULL CHECK (price_out_micro_per_mtok >= 0),
            valid_from timestamptz NOT NULL,
            valid_to timestamptz,
            CHECK (valid_to IS NULL OR valid_to > valid_from)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE usage_events (
            id uuid PRIMARY KEY,
            request_id uuid NOT NULL UNIQUE,
            occurred_at timestamptz NOT NULL,
            workspace_id uuid NOT NULL REFERENCES workspaces (id),
            project_id uuid NOT NULL REFERENCES projects (id),
            agent_id uuid NOT NULL REFERENCES agents (id),
            provider text NOT NULL,
            model text NOT NULL,
            tokens_in integer NOT NULL DEFAULT 0 CHECK (tokens_in >= 0),
            tokens_out integer NOT NULL DEFAULT 0 CHECK (tokens_out >= 0),
            usage_estimated boolean NOT NULL DEFAULT false,
            price_in_micro_per_mtok bigint,
            price_out_micro_per_mtok bigint,
            cost_micro_usd bigint NOT NULL DEFAULT 0 CHECK (cost_micro_usd >= 0),
            latency_ms integer,
            status text NOT NULL CHECK (status IN
                ('success', 'interrupted', 'provider_error', 'timeout', 'budget_refused')),
            error_code text,
            cache_hit boolean NOT NULL DEFAULT false
        )
        """
    )
    op.execute("CREATE INDEX usage_ws_time ON usage_events (workspace_id, occurred_at DESC)")
    op.execute("CREATE INDEX usage_agent_time ON usage_events (agent_id, occurred_at DESC)")
    op.execute("CREATE INDEX usage_project_time ON usage_events (project_id, occurred_at DESC)")
    op.execute("CREATE INDEX usage_ws_cost ON usage_events (workspace_id, cost_micro_usd DESC)")
    op.execute(
        """
        CREATE TABLE budgets (
            id uuid PRIMARY KEY,
            workspace_id uuid NOT NULL REFERENCES workspaces (id),
            agent_id uuid REFERENCES agents (id),
            project_id uuid REFERENCES projects (id),
            period text NOT NULL CHECK (period IN ('day', 'month')),
            limit_micro_usd bigint NOT NULL CHECK (limit_micro_usd > 0),
            alert_threshold_pct smallint NOT NULL
                CHECK (alert_threshold_pct BETWEEN 1 AND 99),
            action_at_limit text NOT NULL CHECK (action_at_limit IN ('block', 'alert_only')),
            created_at timestamptz NOT NULL DEFAULT now(),
            archived_at timestamptz,
            CHECK ((agent_id IS NULL) <> (project_id IS NULL))
        )
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX budgets_agent_period ON budgets (agent_id, period)
            WHERE agent_id IS NOT NULL AND archived_at IS NULL
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX budgets_project_period ON budgets (project_id, period)
            WHERE project_id IS NOT NULL AND archived_at IS NULL
        """
    )
    op.execute(
        """
        CREATE TABLE budget_counters (
            budget_id uuid NOT NULL REFERENCES budgets (id),
            period_start timestamptz NOT NULL,
            spent_micro_usd bigint NOT NULL DEFAULT 0 CHECK (spent_micro_usd >= 0),
            PRIMARY KEY (budget_id, period_start)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE alerts (
            id uuid PRIMARY KEY,
            budget_id uuid NOT NULL REFERENCES budgets (id),
            period_start timestamptz NOT NULL,
            level text NOT NULL CHECK (level IN ('threshold', 'exhausted')),
            triggered_at timestamptz NOT NULL DEFAULT now(),
            delivery_status text NOT NULL DEFAULT 'pending'
                CHECK (delivery_status IN ('pending', 'sent', 'failed')),
            attempts smallint NOT NULL DEFAULT 0,
            delivered_at timestamptz,
            UNIQUE (budget_id, period_start, level)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE admin_sessions (
            id uuid PRIMARY KEY,
            token_hash bytea NOT NULL UNIQUE,
            csrf_hash bytea NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            expires_at timestamptz NOT NULL,
            revoked_at timestamptz
        )
        """
    )


def downgrade() -> None:
    for table in TABLES_DROP_ORDER:
        op.execute(f"DROP TABLE IF EXISTS {table}")
