"""add channels and feature_flags tables

Revision ID: 8e3f4c2d9c01
Revises: 5c1e3c9c2b4b
Create Date: 2025-08-17
"""
from alembic import op
import sqlalchemy as sa

revision = '8e3f4c2d9c01'
down_revision = '5c1e3c9c2b4b'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'channels',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('username', sa.String(length=64), nullable=False, unique=True),
        sa.Column('chat_id', sa.BigInteger(), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('is_required', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        'feature_flags',
        sa.Column('key', sa.String(length=100), primary_key=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

def downgrade() -> None:
    op.drop_table('feature_flags')
    op.drop_table('channels')
