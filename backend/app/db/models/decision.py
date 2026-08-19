"""
Module 9 — Decision Advisor database models.

All UUID columns use GUID() — the same TypeDecorator as every other model
in this project. On Postgres GUID() maps to native UUID; on SQLite to
CHAR(36). This matches the types used by organizations, users, and datasets.

Tables
------
DecisionSession         One analysis run (dataset + org context).
Recommendation          Individual recommendation within a session.
BusinessRule            Configurable IF/THEN rules per org.
RecommendationTemplate  Reusable recommendation text templates.
"""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, GUID, TimestampMixin, UUIDPrimaryKeyMixin


class DecisionSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One decision-analysis run tied to a dataset and organisation."""

    __tablename__ = "decision_sessions"

    # FK to datasets.id — GUID() matches the type used in the datasets table
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # org_id and user_id are not FK-constrained (no organisations/users table
    # constraint in the migration) but use the same GUID type for consistency
    org_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False)

    session_type: Mapped[str] = mapped_column(String(50), nullable=False, default="analysis")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    context_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ai_response: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    recommendations: Mapped[list["Recommendation"]] = relationship(
        "Recommendation", back_populates="session", cascade="all, delete-orphan"
    )


class Recommendation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Single actionable recommendation within a DecisionSession."""

    __tablename__ = "recommendations"

    # FK to decision_sessions.id — GUID() matches the PK type
    session_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("decision_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    org_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="executive")
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")

    # Scores — all 0-100
    priority_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    impact_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    urgency_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    effort_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    roi_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)

    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    business_impact: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_gain: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk: Mapped[str | None] = mapped_column(Text, nullable=True)
    implementation_difficulty: Mapped[str | None] = mapped_column(String(20), nullable=True)
    timeline: Mapped[str | None] = mapped_column(String(50), nullable=True)

    session: Mapped["DecisionSession"] = relationship(
        "DecisionSession", back_populates="recommendations"
    )


class BusinessRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Configurable IF/THEN business rule per organisation."""

    __tablename__ = "business_rules"

    org_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Condition: IF metric_name operator threshold
    metric_name: Mapped[str] = mapped_column(String(255), nullable=False)
    operator: Mapped[str] = mapped_column(String(10), nullable=False, default="lt")
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    threshold_unit: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Then: fire this recommendation
    recommendation_title: Mapped[str] = mapped_column(String(255), nullable=False)
    recommendation_description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="executive")
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")


class RecommendationTemplate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Reusable recommendation templates (system-wide, not per-org)."""

    __tablename__ = "recommendation_templates"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    title_template: Mapped[str] = mapped_column(String(255), nullable=False)
    description_template: Mapped[str] = mapped_column(Text, nullable=False)
    default_priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    tags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
