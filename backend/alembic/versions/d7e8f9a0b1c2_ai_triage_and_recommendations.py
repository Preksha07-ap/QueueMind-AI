"""ai_triage_and_recommendations

Revision ID: d7e8f9a0b1c2
Revises: 83d33ab31a1c
Create Date: 2026-11-20 00:52:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7e8f9a0b1c2'
down_revision: Union[str, None] = '83d33ab31a1c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tickets', sa.Column('ai_recommended_department_id', sa.BigInteger(), nullable=True))
    op.add_column('tickets', sa.Column('ai_recommended_support_team_id', sa.BigInteger(), nullable=True))
    op.add_column('tickets', sa.Column('ai_duplicate_ticket_id', sa.BigInteger(), nullable=True))
    op.add_column('tickets', sa.Column('ai_duplicate_score', sa.Float(), nullable=True))
    op.add_column('tickets', sa.Column('ai_confidence_score', sa.Float(), nullable=True))
    op.add_column('tickets', sa.Column('ai_analysis_status', sa.String(length=50), nullable=True))
    op.add_column('tickets', sa.Column('ai_evidence_json', sa.Text(), nullable=True))

    op.create_foreign_key(
        'fk_tickets_ai_rec_dept',
        'tickets', 'departments',
        ['ai_recommended_department_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_tickets_ai_rec_team',
        'tickets', 'support_teams',
        ['ai_recommended_support_team_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_tickets_ai_duplicate',
        'tickets', 'tickets',
        ['ai_duplicate_ticket_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_tickets_ai_duplicate', 'tickets', type_='foreignkey')
    op.drop_constraint('fk_tickets_ai_rec_team', 'tickets', type_='foreignkey')
    op.drop_constraint('fk_tickets_ai_rec_dept', 'tickets', type_='foreignkey')

    op.drop_column('tickets', 'ai_evidence_json')
    op.drop_column('tickets', 'ai_analysis_status')
    op.drop_column('tickets', 'ai_confidence_score')
    op.drop_column('tickets', 'ai_duplicate_score')
    op.drop_column('tickets', 'ai_duplicate_ticket_id')
    op.drop_column('tickets', 'ai_recommended_support_team_id')
    op.drop_column('tickets', 'ai_recommended_department_id')
