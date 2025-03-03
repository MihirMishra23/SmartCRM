"""add missing columns to emails table

Revision ID: add_missing_columns
Revises: ead2053ab31b
Create Date: 2025-03-03 02:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "add_missing_columns"
down_revision = "ead2053ab31b"
branch_labels = None
depends_on = None


def upgrade():
    # Add subject column to emails table
    op.add_column("emails", sa.Column("subject", sa.Text(), nullable=True))

    # Update existing rows to have a default subject
    op.execute("UPDATE emails SET subject = 'No Subject' WHERE subject IS NULL")

    # Make subject not nullable after setting default values
    op.alter_column("emails", "subject", nullable=False)

    # Add sender_id column to emails table
    op.add_column("emails", sa.Column("sender_id", sa.Integer(), nullable=True))

    # Add foreign key constraint
    op.create_foreign_key(
        "fk_emails_sender_id_contacts",
        "emails",
        "contacts",
        ["sender_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    # Remove foreign key constraint
    op.drop_constraint("fk_emails_sender_id_contacts", "emails", type_="foreignkey")

    # Remove columns
    op.drop_column("emails", "sender_id")
    op.drop_column("emails", "subject")
