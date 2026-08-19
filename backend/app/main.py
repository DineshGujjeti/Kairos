from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import (
    ColumnNotFoundError,
    DatasetNotFoundError,
    DatasetParseError,
    DatasetValidationError,
    EmptyFileError,
    FileTooLargeError,
    FormulaError,
    ForecastingModelError,
    InsufficientDataError,
    InvalidColumnTypeError,
    InvalidParameterError,
    KairosError,
    NoDatetimeColumnError,
    NoNumericColumnsError,
    UnsupportedFileTypeError,
)
from app.core.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("kairos_startup", environment=settings.ENVIRONMENT)
    yield
    logger.info("kairos_shutdown")


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    lifespan=lifespan,
)

if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin).rstrip("/") for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# --- Centralized domain-exception -> HTTP mapping ---
# Each service raises the exception that best describes what went
# wrong (see app/core/exceptions.py); routes never catch these
# themselves. This is what keeps the mapping to HTTP status codes
# defined in exactly one place instead of duplicated per endpoint --
# and it's what the EDA routes' get_dataset_or_404()/read_dataset_file()
# calls rely on for their 404/422 responses.
_ERROR_STATUS_MAP = {
    DatasetNotFoundError: 404,
    UnsupportedFileTypeError: 415,
    FileTooLargeError: 413,
    EmptyFileError: 422,
    DatasetParseError: 422,
    DatasetValidationError: 422,
    ColumnNotFoundError: 404,
    InvalidColumnTypeError: 422,
    InvalidParameterError: 422,
    FormulaError: 422,
    NoDatetimeColumnError: 422,
    InsufficientDataError: 422,
    NoNumericColumnsError: 422,
    ForecastingModelError: 422,
}


@app.exception_handler(KairosError)
async def kairos_error_handler(request: Request, exc: KairosError):
    status_code = _ERROR_STATUS_MAP.get(type(exc), 400)
    logger.warning(
        "domain_error",
        path=str(request.url.path),
        error_type=type(exc).__name__,
        detail=str(exc),
    )
    return JSONResponse(status_code=status_code, content={"detail": str(exc)})


app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["health"])
def health_check() -> dict:
    """Liveness/readiness probe target for Docker/orchestration."""
    return {"status": "ok", "service": settings.PROJECT_NAME}
