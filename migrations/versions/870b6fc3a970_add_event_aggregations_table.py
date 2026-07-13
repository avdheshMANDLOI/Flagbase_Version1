"""add_event_aggregations_table

Revision ID: 870b6fc3a970
Revises: 179916335d1a
Create Date: 2026-07-12 12:54:42.425605

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '870b6fc3a970'
down_revision: Union[str, Sequence[str], None] = '179916335d1a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'event_aggregations',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('flag_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('hour', sa.DateTime(timezone=True), nullable=False),
        sa.Column('variation', sa.String(length=50), nullable=False),
        sa.Column('count', sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('flag_id', 'hour', 'variation', name='uq_event_agg_flag_hour_variation'),
    )
    op.create_index('idx_event_agg_flag_id_hour', 'event_aggregations', ['flag_id', 'hour'])


def downgrade() -> None:
    op.drop_index('idx_event_agg_flag_id_hour', table_name='event_aggregations')
    op.drop_table('event_aggregations')
