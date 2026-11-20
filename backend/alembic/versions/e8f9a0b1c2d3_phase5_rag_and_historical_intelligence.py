"""phase5_rag_and_historical_intelligence

Revision ID: e8f9a0b1c2d3
Revises: d7e8f9a0b1c2
Create Date: 2026-11-20 03:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8f9a0b1c2d3'
down_revision: Union[str, None] = 'd7e8f9a0b1c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Organizations
    op.add_column('organizations', sa.Column('is_demo', sa.Boolean(), server_default=sa.false(), nullable=False))

    # 2. Users
    op.add_column('users', sa.Column('is_demo', sa.Boolean(), server_default=sa.false(), nullable=False))

    # 3. Tickets
    op.add_column('tickets', sa.Column('related_incident_id', sa.BigInteger(), nullable=True))
    op.add_column('tickets', sa.Column('verified_resolution', sa.Text(), nullable=True))
    op.add_column('tickets', sa.Column('is_resolution_verified', sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column('tickets', sa.Column('is_demo', sa.Boolean(), server_default=sa.false(), nullable=False))

    op.create_foreign_key(
        'fk_tickets_related_incident',
        'tickets', 'tickets',
        ['related_incident_id'], ['id'],
        ondelete='SET NULL'
    )

    # 4. KnowledgeBase
    op.add_column('knowledge_base', sa.Column('symptoms', sa.Text(), nullable=True))
    op.add_column('knowledge_base', sa.Column('possible_causes', sa.Text(), nullable=True))
    op.add_column('knowledge_base', sa.Column('troubleshooting_steps', sa.Text(), nullable=True))
    op.add_column('knowledge_base', sa.Column('verified_resolution', sa.Text(), nullable=True))
    op.add_column('knowledge_base', sa.Column('source_type', sa.String(length=50), server_default='MANUAL_KB', nullable=True))
    op.add_column('knowledge_base', sa.Column('source_ticket_id', sa.BigInteger(), nullable=True))
    op.add_column('knowledge_base', sa.Column('tags', sa.String(length=500), nullable=True))
    op.add_column('knowledge_base', sa.Column('version', sa.String(length=50), server_default='1.0', nullable=True))
    op.add_column('knowledge_base', sa.Column('is_demo', sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column('knowledge_base', sa.Column('is_verified', sa.Boolean(), server_default=sa.true(), nullable=False))

    op.create_foreign_key(
        'fk_knowledge_base_source_ticket',
        'knowledge_base', 'tickets',
        ['source_ticket_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_knowledge_base_source_ticket', 'knowledge_base', type_='foreignkey')
    op.drop_column('knowledge_base', 'is_verified')
    op.drop_column('knowledge_base', 'is_demo')
    op.drop_column('knowledge_base', 'version')
    op.drop_column('knowledge_base', 'tags')
    op.drop_column('knowledge_base', 'source_ticket_id')
    op.drop_column('knowledge_base', 'source_type')
    op.drop_column('knowledge_base', 'verified_resolution')
    op.drop_column('knowledge_base', 'troubleshooting_steps')
    op.drop_column('knowledge_base', 'possible_causes')
    op.drop_column('knowledge_base', 'symptoms')

    op.drop_constraint('fk_tickets_related_incident', 'tickets', type_='foreignkey')
    op.drop_column('tickets', 'is_demo')
    op.drop_column('tickets', 'is_resolution_verified')
    op.drop_column('tickets', 'verified_resolution')
    op.drop_column('tickets', 'related_incident_id')

    op.drop_column('users', 'is_demo')
    op.drop_column('organizations', 'is_demo')
