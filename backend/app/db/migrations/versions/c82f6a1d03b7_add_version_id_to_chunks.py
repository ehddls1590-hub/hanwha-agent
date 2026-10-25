"""complete chunk schema

Revision ID: c82f6a1d03b7
Revises: b3e07dd8994d
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c82f6a1d03b7"
down_revision: Union[str, Sequence[str], None] = "b3e07dd8994d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("chunks") as batch_op:
        batch_op.add_column(
            sa.Column(
                "version_id",
                sa.Integer(),
                sa.ForeignKey(
                    "document_versions.id",
                    name="fk_chunks_version_id_document_versions",
                ),
                nullable=True,
            )
        )
        batch_op.add_column(sa.Column("ord", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("kind", sa.String(length=16), nullable=True))
        batch_op.add_column(sa.Column("locator", sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column("text", sa.Text(), nullable=True))
    op.create_index("ix_chunks_version_id", "chunks", ["version_id"])


def downgrade() -> None:
    op.drop_index("ix_chunks_version_id", table_name="chunks")
    with op.batch_alter_table("chunks") as batch_op:
        batch_op.drop_constraint(
            "fk_chunks_version_id_document_versions",
            type_="foreignkey",
        )
        batch_op.drop_column("text")
        batch_op.drop_column("locator")
        batch_op.drop_column("kind")
        batch_op.drop_column("ord")
        batch_op.drop_column("version_id")
