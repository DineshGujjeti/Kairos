"""
Dataset loading for the KPI engine.

Deliberately thin: it does exactly one thing (resolve dataset_id ->
DataFrame, org-scoped) by reusing the two functions Module 2 already
built for this -- `get_dataset_or_404` (persistence + tenant isolation)
and `read_dataset_file` (pandas parsing). No new file-reading logic is
introduced here; this module is a consumer, not a reimplementation.

Every analytics module (EDA, KPI, Forecasting, Root Cause, Simulation,
Decision) funnels through load_dataframe(), which made it the highest-
leverage place to fix the "re-reads the file from disk on every single
request" performance problem: the parsed DataFrame is now cached per
dataset for a short TTL, keyed on the dataset's own updated_at so a
re-processed dataset naturally invalidates itself.

The tenant-isolation check (get_dataset_or_404) always runs on every
call, cache hit or miss -- caching only skips the disk read + pandas
parse, never the authorization check.
"""
import uuid

import pandas as pd
from sqlalchemy.orm import Session

from app.core.cache import TTLCache
from app.db.models.user import User
from app.services.dataset_service import get_dataset_or_404
from app.services.ingestion_service import read_dataset_file

# Parsed DataFrames are the most expensive, most-repeated piece of work
# in the whole request path (every module re-derives everything else
# from this). 5 minute TTL: long enough to eliminate the redundant
# disk-read-per-request pattern within a single analysis session, short
# enough that memory doesn't grow unbounded across a long-running
# process with many datasets in rotation.
_dataframe_cache: TTLCache[pd.DataFrame] = TTLCache(max_size=32, ttl_seconds=300.0)


def load_dataframe(dataset_id: uuid.UUID, db: Session, current_user: User) -> pd.DataFrame:
    """
    Resolves a dataset by id, scoped to the current user's organization
    (raises DatasetNotFoundError -- mapped to 404 -- for missing or
    cross-tenant datasets, exactly as Module 2's own endpoints do), then
    reads it into a DataFrame via the same pandas entry point Module 2
    and Module 3 already use -- cached per (dataset_id, updated_at).

    Returns a COPY of the cached DataFrame. Callers across this codebase
    routinely mutate the frame they receive (dropping columns, encoding,
    filling NaNs); since the cache instance is shared and safe-for-reads
    only, handing out a `.copy()` here is what keeps that mutation from
    corrupting the cached original for the next caller.
    """
    dataset = get_dataset_or_404(db=db, dataset_id=dataset_id, org_id=current_user.org_id)
    cache_key = (str(dataset.id), dataset.updated_at.isoformat() if dataset.updated_at else None)

    def _read() -> pd.DataFrame:
        extension = dataset.original_filename.rsplit(".", 1)[-1].lower()
        return read_dataset_file(dataset.file_path, extension)

    df = _dataframe_cache.get_or_compute(cache_key, _read)
    return df.copy()


def invalidate_dataframe_cache(dataset_id: uuid.UUID) -> None:
    """Called on dataset delete so a reused id (unlikely with UUIDs, but
    cheap to be correct about) or a future re-processing flow can't ever
    serve a stale cached frame."""
    _dataframe_cache.delete_prefix(str(dataset_id))
