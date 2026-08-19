from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Even a single-tenant final-year deployment benefits from modeling
    Organization as a first-class entity from the start: every future
    table (datasets, model_runs, recommendations, ...) scopes to
    org_id, so multi-tenancy is a schema property you already have
    rather than a migration you'd need to retrofit later.
    """

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    users: Mapped[list["User"]] = relationship(back_populates="organization")
    datasets: Mapped[list["Dataset"]] = relationship(back_populates="organization")
