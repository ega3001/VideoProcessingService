"""name

Revision ID: 24d6e9ea3eab
Revises: 26214c78b594
Create Date: 2023-10-06 20:29:40.516404

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '24d6e9ea3eab'
down_revision = '26214c78b594'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('interviews')
    op.add_column('localizations', sa.Column('duration_in_sec', sa.Float(), nullable=True))
    op.add_column('localizations', sa.Column('estimated_completion_date', sa.DateTime(), nullable=True))
    op.drop_column('localizations', 'duration')
    op.add_column('projects', sa.Column('duration_in_sec', sa.Float(), nullable=True))
    op.drop_column('projects', 'duration')
    op.add_column('subscriptions', sa.Column('meta', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.drop_column('subscriptions', 'price')
    op.add_column('user_subscriptions', sa.Column('stripe_sub_id', sa.String(), nullable=False))
    op.add_column('user_subscriptions', sa.Column('renewal_active', sa.Boolean(), nullable=False))
    op.add_column('user_subscriptions', sa.Column('updated', sa.DateTime(), nullable=True))
    op.drop_constraint('user_subscriptions_payment_id_fkey', 'user_subscriptions', type_='foreignkey')
    op.drop_column('user_subscriptions', 'payment_id')
    op.drop_column('users', 'sub_is_active')
    op.drop_column('users', 'stripe_sub_id')
    op.drop_column('users', 'sub_until')
    op.drop_table('payments')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('sub_until', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.add_column('users', sa.Column('stripe_sub_id', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('users', sa.Column('sub_is_active', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.add_column('user_subscriptions', sa.Column('payment_id', postgresql.UUID(), autoincrement=False, nullable=False))
    op.create_foreign_key('user_subscriptions_payment_id_fkey', 'user_subscriptions', 'payments', ['payment_id'], ['id'])
    op.drop_column('user_subscriptions', 'updated')
    op.drop_column('user_subscriptions', 'renewal_active')
    op.drop_column('user_subscriptions', 'stripe_sub_id')
    op.add_column('subscriptions', sa.Column('price', sa.INTEGER(), autoincrement=False, nullable=False))
    op.drop_column('subscriptions', 'meta')
    op.add_column('projects', sa.Column('duration', postgresql.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True))
    op.drop_column('projects', 'duration_in_sec')
    op.add_column('localizations', sa.Column('duration', postgresql.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True))
    op.drop_column('localizations', 'estimated_completion_date')
    op.drop_column('localizations', 'duration_in_sec')
    op.create_table('interviews',
    sa.Column('id', postgresql.UUID(), autoincrement=False, nullable=False),
    sa.Column('user_id', postgresql.UUID(), autoincrement=False, nullable=False),
    sa.Column('created', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('updated', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('message', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('status', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='interviews_user_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='interviews_pkey')
    )
    op.create_table('payments',
    sa.Column('id', postgresql.UUID(), autoincrement=False, nullable=False),
    sa.Column('user_id', postgresql.UUID(), autoincrement=False, nullable=False),
    sa.Column('stripe_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('amount', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('date', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='payments_user_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='payments_pkey')
    )
    # ### end Alembic commands ###