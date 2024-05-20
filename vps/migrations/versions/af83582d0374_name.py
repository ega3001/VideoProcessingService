"""name

Revision ID: af83582d0374
Revises: 2f9647bf996c
Create Date: 2023-12-07 18:40:47.780315

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'af83582d0374'
down_revision = '2f9647bf996c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('localizations', sa.Column('target_voice_name', sa.String(), nullable=False, server_default=""))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('localizations', 'target_voice_name')
    # ### end Alembic commands ###