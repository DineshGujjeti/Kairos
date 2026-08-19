import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.dataset import DatasetStatus, DatasetType


class DatasetUploadForm(BaseModel):
    """
    Mirrors the non-file form fields sent alongside the multipart file
    upload. FastAPI can't use a Pydantic model directly for multipart
    forms with a file field (see routes.py, which uses `Form(...)`
    parameters instead) -- this class exists purely to document the
    expected shape in one place and for reuse in tests.
    """

    dataset_type: DatasetType = DatasetType.GENERAL
    name: str | None = Field(
        default=None,
        max_length=255,
        description="Defaults to the uploaded filename if not provided",
    )


class DatasetRead(BaseModel):
    # populate_by_name lets from_attributes still populate this field
    # from the ORM's `schema_json` attribute despite the Python-level
    # name below being different -- see the Field(alias=...) note.
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    org_id: uuid.UUID
    uploaded_by: uuid.UUID
    name: str
    dataset_type: DatasetType
    original_filename: str
    file_size_bytes: int
    row_count: int | None
    column_count: int | None
    # Named schema_definition on the Python side (not schema_json)
    # because BaseModel has a deprecated built-in `schema_json()`
    # method and Pydantic warns loudly about the name collision.
    # `alias="schema_json"` keeps the actual JSON API field name and
    # the ORM attribute name unchanged.
    schema_definition: dict | None = Field(default=None, alias="schema_json")
    # Dynamic column-role profile from dataset_intelligence.profile_dataset
    # -- domain guess, detected id/datetime/measure/dimension columns,
    # ranked target/datetime candidates. None only if profiling itself
    # failed (never blocks the upload -- see routes.py).
    column_profile: dict | None = None
    status: DatasetStatus
    status_message: str | None
    validation_errors: dict | None
    created_at: datetime
    updated_at: datetime


class DatasetListItem(BaseModel):
    """Slimmer shape for list views -- omits schema_json/validation_errors,
    which can be large and aren't needed until a single dataset is opened.
    domain_guess is a lightweight extract from the fuller column_profile,
    populated explicitly in dataset_service.list_datasets (not via
    automatic from_attributes conversion, since it isn't a plain ORM
    column) so the dataset list itself hints at what kind of data each
    file contains without a second round trip."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    dataset_type: DatasetType
    status: DatasetStatus
    row_count: int | None
    column_count: int | None
    file_size_bytes: int
    domain_guess: str | None = None
    created_at: datetime


class DatasetListResponse(BaseModel):
    total: int
    items: list[DatasetListItem]


class DatasetPreviewResponse(BaseModel):
    """First N rows of a validated dataset, for a quick sanity check in the UI."""

    columns: list[str]
    rows: list[dict]
    row_count_shown: int
    row_count_total: int | None
