"""name

Revision ID: 2574bf66c7f1
Revises: a0f408d87412
Create Date: 2023-09-21 10:55:22.894945

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '2f9647bf996c'
down_revision = '24d6e9ea3eab'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""INSERT INTO subscriptions(id, duration, type, status, meta) VALUES 
        (gen_random_uuid(), '30 Days', 2, 1, '{"price_id": "price_1No0ZQGWDAzcvhIecrGCmYqP", "min_price_id": "price_1No0YlGWDAzcvhIe6up2pWTz", "display_price": 99.9, "display_currency": "$"}')"""
    )


def downgrade() -> None:
    op.execute("DELETE FROM subscriptions")
