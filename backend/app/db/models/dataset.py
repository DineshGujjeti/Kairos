import enum
import uuid

from sqlalchemy import BigInteger, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, GUID, TimestampMixin, UUIDPrimaryKeyMixin

# JSONB on Postgres (indexable, queryable) with a plain JSON fallback on
# any other dialect -- this is what lets the test suite run against
# SQLite (see tests/conftest.py) while production uses real JSONB.
PortableJSON = JSON().with_variant(JSONB(), "postgresql")


class DatasetType(str, enum.Enum):
    """
    The six supply-chain/inventory categories get structural Pandera
    validation (see dataset_validation_schemas.py) because their column
    shape is known in advance. GENERAL covers everything else -- any
    business domain (HR, finance, healthcare, marketing, IoT, ...) -- and
    is profiled dynamically instead via dataset_intelligence.profile_dataset,
    with no fixed schema requirement. GENERAL is also the default so
    uploading a dataset never requires the user to force-fit an unrelated
    category just to get past validation.
    """

    GENERAL = "general"
    ORDERS = "orders"
    PRODUCTS = "products"
    INVENTORY = "inventory"
    WAREHOUSES = "warehouses"
    SUPPLIERS = "suppliers"
    DELIVERIES = "deliveries"


class DatasetStatus(str, enum.Enum):
    UPLOADED = "uploaded"       # file stored, not yet validated
    VALIDATING = "validating"   # validation in progress
    VALID = "valid"             # passed structural validation
    INVALID = "invalid"         # failed validation (see validation_errors)
    FAILED = "failed"           # unexpected error during processing


class Dataset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "datasets"

    org_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organizations.id"), nullable=False, index=True
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    dataset_type: Mapped[DatasetType] = mapped_column(
    Enum(
        DatasetType,
        name="dataset_type",
        values_callable=lambda obj: [e.value for e in obj],
    ),
    nullable=False,
    index=True,
)

    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)

    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    column_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # See PortableJSON definition above for why this isn't raw JSONB.
    schema_json: Mapped[dict | None] = mapped_column(PortableJSON, nullable=True)
    validation_errors: Mapped[dict | None] = mapped_column(PortableJSON, nullable=True)

    # Output of dataset_intelligence.profile_dataset() -- dynamic column
    # role detection (id/datetime/measure/dimension/...), domain guess,
    # and ranked target/datetime candidates. Populated for every dataset
    # regardless of dataset_type, so downstream modules and the frontend
    # always have a dataset-agnostic picture of "what did we detect".
    column_profile: Mapped[dict | None] = mapped_column(PortableJSON, nullable=True)

    status: Mapped[DatasetStatus] = mapped_column(
        Enum(
    DatasetStatus,
    name="dataset_status",
    values_callable=lambda obj: [e.value for e in obj],
),
        default=DatasetStatus.UPLOADED,
        nullable=False,
    )
    status_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    organization: Mapped["Organization"] = relationship(back_populates="datasets")
    uploaded_by_user: Mapped["User"] = relationship(back_populates="datasets")
