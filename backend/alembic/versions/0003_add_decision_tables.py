"""add decision advisor tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

# Shorthand — every UUID column in this project uses the same type
_UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    # ── decision_sessions ──────────────────────────────────────────────────
    op.create_table(
        "decision_sessions",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column(
            "dataset_id",
            _UUID,
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("org_id", _UUID, nullable=False),
        sa.Column("user_id", _UUID, nullable=False),
        sa.Column("session_type", sa.String(50), nullable=False, server_default="analysis"),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("context_snapshot", sa.JSON, nullable=True),
        sa.Column("ai_response", sa.JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_decision_sessions_dataset_id", "decision_sessions", ["dataset_id"])
    op.create_index("ix_decision_sessions_org_id", "decision_sessions", ["org_id"])

    # ── recommendations ────────────────────────────────────────────────────
    op.create_table(
        "recommendations",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column(
            "session_id",
            _UUID,
            sa.ForeignKey("decision_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("org_id", _UUID, nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("category", sa.String(50), nullable=False, server_default="executive"),
        sa.Column("priority", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("priority_score", sa.Float, nullable=False, server_default="50"),
        sa.Column("impact_score", sa.Float, nullable=False, server_default="50"),
        sa.Column("confidence_score", sa.Float, nullable=False, server_default="50"),
        sa.Column("urgency_score", sa.Float, nullable=False, server_default="50"),
        sa.Column("effort_score", sa.Float, nullable=False, server_default="50"),
        sa.Column("roi_score", sa.Float, nullable=False, server_default="50"),
        sa.Column("overall_score", sa.Float, nullable=False, server_default="50"),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("business_impact", sa.Text, nullable=True),
        sa.Column("expected_gain", sa.Text, nullable=True),
        sa.Column("risk", sa.Text, nullable=True),
        sa.Column("implementation_difficulty", sa.String(20), nullable=True),
        sa.Column("timeline", sa.String(50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_recommendations_session_id", "recommendations", ["session_id"])
    op.create_index("ix_recommendations_org_id", "recommendations", ["org_id"])

    # ── business_rules ─────────────────────────────────────────────────────
    op.create_table(
        "business_rules",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("org_id", _UUID, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("metric_name", sa.String(255), nullable=False),
        sa.Column("operator", sa.String(10), nullable=False, server_default="lt"),
        sa.Column("threshold", sa.Float, nullable=False),
        sa.Column("threshold_unit", sa.String(50), nullable=True),
        sa.Column("recommendation_title", sa.String(255), nullable=False),
        sa.Column("recommendation_description", sa.Text, nullable=False),
        sa.Column("category", sa.String(50), nullable=False, server_default="executive"),
        sa.Column("priority", sa.String(20), nullable=False, server_default="medium"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_business_rules_org_id", "business_rules", ["org_id"])

    # ── recommendation_templates ───────────────────────────────────────────
    op.create_table(
        "recommendation_templates",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("title_template", sa.String(255), nullable=False),
        sa.Column("description_template", sa.Text, nullable=False),
        sa.Column("default_priority", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("tags", sa.JSON, nullable=True),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("recommendation_templates")
    op.drop_index("ix_business_rules_org_id", table_name="business_rules")
    op.drop_table("business_rules")
    op.drop_index("ix_recommendations_org_id", table_name="recommendations")
    op.drop_index("ix_recommendations_session_id", table_name="recommendations")
    op.drop_table("recommendations")
    op.drop_index("ix_decision_sessions_org_id", table_name="decision_sessions")
    op.drop_index("ix_decision_sessions_dataset_id", table_name="decision_sessions")
    op.drop_table("decision_sessions")
