"""Create uploaded_evidence table

Revision ID: 001
Revises: 
Create Date: 2026-09-08 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create uploaded_evidence table
    op.create_table(
        "uploaded_evidence",
        sa.Column("evidence_id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("incident_id", sa.String(length=64), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.String(length=64), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("storage_uri", sa.Text(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processing_status", sa.String(length=32), nullable=False),
        sa.Column("sha256_hash", sa.String(length=64), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default="{}"),
    )

    # Create explicit secondary indexes for fast filtering and joins
    op.create_index(
        "ix_uploaded_evidence_incident_id",
        "uploaded_evidence",
        ["incident_id"],
        unique=False,
    )
    op.create_index(
        "ix_uploaded_evidence_asset_id",
        "uploaded_evidence",
        ["asset_id"],
        unique=False,
    )
    op.create_index(
        "ix_uploaded_evidence_source_type",
        "uploaded_evidence",
        ["source_type"],
        unique=False,
    )
    op.create_index(
        "ix_uploaded_evidence_processing_status",
        "uploaded_evidence",
        ["processing_status"],
        unique=False,
    )
    op.create_index(
        "ix_uploaded_evidence_sha256_hash",
        "uploaded_evidence",
        ["sha256_hash"],
        unique=False,
    )
    op.create_index(
        "ix_uploaded_evidence_uploaded_at",
        "uploaded_evidence",
        ["uploaded_at"],
        unique=False,
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_uploaded_evidence_uploaded_at", table_name="uploaded_evidence")
    op.drop_index("ix_uploaded_evidence_sha256_hash", table_name="uploaded_evidence")
    op.drop_index("ix_uploaded_evidence_processing_status", table_name="uploaded_evidence")
    op.drop_index("ix_uploaded_evidence_source_type", table_name="uploaded_evidence")
    op.drop_index("ix_uploaded_evidence_asset_id", table_name="uploaded_evidence")
    op.drop_index("ix_uploaded_evidence_incident_id", table_name="uploaded_evidence")

    # Drop table
    op.drop_table("uploaded_evidence")
