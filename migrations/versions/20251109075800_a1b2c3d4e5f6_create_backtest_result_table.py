"""create_backtest_result_table

Revision ID: a1b2c3d4e5f6
Revises: 674dd0dcf86a
Create Date: 2025-11-09 07:58:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "674dd0dcf86a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create backtest_result table with all parameters
    op.create_table(
        "backtest_result",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        # Backtest parameters for duplicate detection
        sa.Column("params_hash", sa.String(), nullable=False),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("strategy_name", sa.String(), nullable=False),
        sa.Column("start_date", sa.DateTime(), nullable=False),
        sa.Column("end_date", sa.DateTime(), nullable=False),
        sa.Column("signal_interval_minutes", sa.Integer(), nullable=False),
        sa.Column("candle_interval", sa.String(), nullable=False),
        sa.Column("lookback_periods", sa.Integer(), nullable=False),
        sa.Column("position_size_usd", sa.Float(), nullable=False),
        sa.Column("strategy_params", sa.JSON(), nullable=True),
        # Results
        sa.Column("total_trades", sa.Integer(), nullable=False),
        sa.Column("total_return_percent", sa.Float(), nullable=False),
        sa.Column("win_rate", sa.Float(), nullable=False),
        sa.Column("total_income", sa.Float(), nullable=False),
        sa.Column("total_volume", sa.Float(), nullable=False),
        sa.Column("trades_data", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id"),
    )

    # Create index on params_hash for fast duplicate detection
    op.create_index("ix_backtest_result_params_hash", "backtest_result", ["params_hash"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_backtest_result_params_hash", "backtest_result")
    op.drop_table("backtest_result")
