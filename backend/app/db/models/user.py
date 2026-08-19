import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, GUID, TimestampMixin, UUIDPrimaryKeyMixin


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
    Enum(
        UserRole,
        name="user_role",
        values_callable=lambda obj: [e.value for e in obj],
    ),
    default=UserRole.VIEWER,
    nullable=False,
)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    org_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organizations.id"), nullable=False
    )
    organization: Mapped["Organization"] = relationship(back_populates="users")
    datasets: Mapped[list["Dataset"]] = relationship(back_populates="uploaded_by_user")
