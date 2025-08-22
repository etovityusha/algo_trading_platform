"""populate sell_price for existing records

Revision ID: 674dd0dcf86a
Revises: d2e4f5a6b7c9
Create Date: 2025-08-22 08:32:26.639975

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "674dd0dcf86a"
down_revision: str | None = "d2e4f5a6b7c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Populate sell_price for existing closed positions
    # For TP executed positions, use take_profit_price
    # For SL executed positions, use stop_loss_price
    # For manually closed positions without sell_price, use price (buy price as fallback)

    connection = op.get_bind()

    # Update TP executed positions
    connection.execute(
        sa.text(
            """
        UPDATE deal
        SET sell_price = take_profit_price
        WHERE is_take_profit_executed = true
        AND sell_price IS NULL
        AND take_profit_price IS NOT NULL
    """
        )
    )

    # Update SL executed positions
    connection.execute(
        sa.text(
            """
        UPDATE deal
        SET sell_price = stop_loss_price
        WHERE is_stop_loss_executed = true
        AND sell_price IS NULL
        AND stop_loss_price IS NOT NULL
    """
        )
    )

    # Update manually closed positions (use buy price as fallback)
    connection.execute(
        sa.text(
            """
        UPDATE deal
        SET sell_price = price
        WHERE is_manually_closed = true
        AND sell_price IS NULL
        AND price IS NOT NULL
    """
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Reset sell_price for records that were populated by this migration
    # We can't easily distinguish which sell_price values were set by this migration
    # vs those set by the application, so we'll leave them as is for safety
    # In a real scenario, you might want to track which records were updated
    pass
