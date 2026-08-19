"""
Domain-level exceptions for dataset ingestion.

These are raised from services (never from route handlers directly) and
mapped to HTTP responses by the exception handlers registered in
app/main.py. Keeping the mapping centralized -- rather than each route
doing its own try/except HTTPException -- means the HTTP status for
"file too large" or "unsupported type" is defined exactly once and
can't drift between endpoints.
"""


class KairosError(Exception):
    """Base class for all domain errors in the application."""


class DatasetNotFoundError(KairosError):
    def __init__(self, dataset_id: str):
        self.dataset_id = dataset_id
        super().__init__(f"Dataset {dataset_id} not found")


class UnsupportedFileTypeError(KairosError):
    def __init__(self, extension: str, allowed: list[str]):
        self.extension = extension
        self.allowed = allowed
        super().__init__(
            f"File type '.{extension}' is not supported. Allowed: {', '.join(allowed)}"
        )


class FileTooLargeError(KairosError):
    def __init__(self, size_mb: float, max_mb: int):
        self.size_mb = size_mb
        self.max_mb = max_mb
        super().__init__(f"File is {size_mb:.1f}MB, which exceeds the {max_mb}MB limit")


class EmptyFileError(KairosError):
    def __init__(self):
        super().__init__("Uploaded file is empty")


class DatasetParseError(KairosError):
    """Raised when pandas cannot parse the uploaded file at all."""

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(f"Could not parse dataset: {detail}")


class DatasetValidationError(KairosError):
    """Raised when the file parses but fails structural validation."""

    def __init__(self, errors: dict):
        self.errors = errors
        super().__init__("Dataset failed structural validation")


# ============================================================
# Module 4 (KPI Engine) exceptions
# ============================================================


class ColumnNotFoundError(KairosError):
    def __init__(self, column: str):
        self.column = column
        super().__init__(f"Column '{column}' was not found in the dataset")


class InvalidColumnTypeError(KairosError):
    def __init__(self, column: str, expected: str):
        self.column = column
        self.expected = expected
        super().__init__(f"Column '{column}' is not of the expected type: {expected}")


class InvalidParameterError(KairosError):
    """Raised for invalid query/body parameters that aren't specific to a column (e.g. an unsupported aggregation or frequency)."""


class FormulaError(KairosError):
    """Raised when a KPI formula fails to parse or references disallowed constructs."""


# ============================================================
# Module 5 (Forecasting Engine) exceptions
# ============================================================


class NoDatetimeColumnError(KairosError):
    def __init__(self):
        super().__init__("Dataset contains no datetime column for time-series forecasting")


class InsufficientDataError(KairosError):
    def __init__(self, required: int = 10, actual: int = 0):
        self.required = required
        self.actual = actual
        super().__init__(
            f"Insufficient data for forecasting: {actual} rows, {required} required"
        )


class NoNumericColumnsError(KairosError):
    def __init__(self):
        super().__init__("Dataset contains no numeric columns to forecast")


class ForecastingModelError(KairosError):
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(f"Forecasting model error: {detail}")
