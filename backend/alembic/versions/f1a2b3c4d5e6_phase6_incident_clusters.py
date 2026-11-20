"""Phase 6 — Incident Cluster Table Migration."""

from alembic import op
import sqlalchemy as sa


revision = "f1a2b3c4d5e6"
down_revision = "e8f9a0b1c2d3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "incident_clusters",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("primary_ticket_id", sa.BigInteger(), nullable=True),
        sa.Column("cluster_number", sa.String(50), nullable=False),
        sa.Column("common_issue_summary", sa.Text(), nullable=True),
        sa.Column("category", sa.String(255), nullable=True),
        sa.Column("incident_priority", sa.String(20), nullable=False, server_default="MEDIUM"),
        sa.Column("status", sa.String(50), nullable=False, server_default="OPEN"),
        sa.Column("related_ticket_ids_json", sa.Text(), nullable=True),
        sa.Column("distinct_affected_users", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("total_reports", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("similarity_score", sa.Float(), nullable=True),
        sa.Column("verified_resolution", sa.Text(), nullable=True),
        sa.Column("escalation_reason", sa.Text(), nullable=True),
        sa.Column("is_confirmed", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("first_reported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_reported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            ondelete="CASCADE", name="fk_incident_clusters_org",
        ),
        sa.ForeignKeyConstraint(
            ["primary_ticket_id"], ["tickets.id"],
            ondelete="SET NULL", name="fk_incident_clusters_primary_ticket",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_incident_clusters_organization_id", "incident_clusters", ["organization_id"])
    op.create_index("ix_incident_clusters_status", "incident_clusters", ["status"])
    op.create_index("ix_incident_clusters_incident_priority", "incident_clusters", ["incident_priority"])
    op.create_index("ix_incident_clusters_first_reported_at", "incident_clusters", ["first_reported_at"])

    # Add cluster_id FK to tickets so a ticket can belong to a cluster
    op.add_column("tickets", sa.Column("incident_cluster_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        "fk_tickets_incident_cluster",
        "tickets", "incident_clusters",
        ["incident_cluster_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_tickets_incident_cluster_id", "tickets", ["incident_cluster_id"])


def downgrade() -> None:
    op.drop_index("ix_tickets_incident_cluster_id", table_name="tickets")
    op.drop_constraint("fk_tickets_incident_cluster", "tickets", type_="foreignkey")
    op.drop_column("tickets", "incident_cluster_id")

    op.drop_index("ix_incident_clusters_first_reported_at", table_name="incident_clusters")
    op.drop_index("ix_incident_clusters_incident_priority", table_name="incident_clusters")
    op.drop_index("ix_incident_clusters_status", table_name="incident_clusters")
    op.drop_index("ix_incident_clusters_organization_id", table_name="incident_clusters")
    op.drop_table("incident_clusters")
