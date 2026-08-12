"""questions and questionnaire feedback

Revision ID: 9f2b1c4e7d83
Revises: cc65dda1cd14
Create Date: 2026-08-12 07:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9f2b1c4e7d83'
down_revision: Union[str, Sequence[str], None] = 'cc65dda1cd14'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('questions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('hospital_id', sa.Integer(), nullable=False),
    sa.Column('text', sa.String(length=500), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('feedback', sa.Column('answers', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=True))
    op.drop_column('feedback', 'text_comment')
    op.drop_column('feedback', 'tags')
    op.drop_column('feedback', 'rating')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('feedback', sa.Column('rating', sa.Integer(), nullable=False))
    op.add_column('feedback', sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=False))
    op.add_column('feedback', sa.Column('text_comment', sa.String(length=2000), nullable=True))
    op.drop_column('feedback', 'answers')
    op.drop_table('questions')
