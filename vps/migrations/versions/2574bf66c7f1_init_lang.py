"""name

Revision ID: 2574bf66c7f1
Revises: a0f408d87412
Create Date: 2023-09-21 10:55:22.894945

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '2574bf66c7f1'
down_revision = 'a0f408d87412'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""INSERT INTO languages(id, lang_name, api_name) VALUES 
        (gen_random_uuid(), 'English', 'en'),
        (gen_random_uuid(), 'Russian', 'ru'),
        (gen_random_uuid(), 'French', 'fr'),
        (gen_random_uuid(), 'German', 'de'),
        (gen_random_uuid(), 'Italian', 'it')"""
    )


def downgrade() -> None:
    op.execute("DELETE FROM languages")
