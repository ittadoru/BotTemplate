"""Add processed_payments table for payment idempotency

Revision ID: 5c1e3c9c2b4b
Revises: d1107b930a1b
Create Date: 2025-08-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '5c1e3c9c2b4b'
down_revision: Union[str, Sequence[str], None] = 'd1107b930a1b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create processed_payments table."""
    op.create_table(
        'processed_payments',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('payment_id', sa.String(length=100), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_unique_constraint('uq_processed_payment_payment_id', 'processed_payments', ['payment_id'])


def downgrade() -> None:
    """Drop processed_payments table."""
    op.drop_constraint('uq_processed_payment_payment_id', 'processed_payments', type_='unique')
    op.drop_table('processed_payments')
