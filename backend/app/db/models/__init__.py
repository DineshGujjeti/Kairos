"""
Import every model here so Alembic's autogenerate can diff the full schema.
"""
from app.db.models.dataset import Dataset, DatasetStatus, DatasetType  # noqa: F401
from app.db.models.organization import Organization  # noqa: F401
from app.db.models.user import User, UserRole  # noqa: F401
from app.db.models.decision import (  # noqa: F401
    DecisionSession,
    Recommendation,
    BusinessRule,
    RecommendationTemplate,
)

__all__ = [
    "Dataset", "DatasetStatus", "DatasetType",
    "Organization",
    "User", "UserRole",
    "DecisionSession", "Recommendation", "BusinessRule", "RecommendationTemplate",
]
