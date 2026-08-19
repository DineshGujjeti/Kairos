"""
DuckDB connection helper (analytical store).

Design rule for the whole project: raw uploaded dataset rows are NEVER
written into PostgreSQL. Postgres holds transactional/application state
(users, dataset *metadata*, model runs, KPI snapshots, recommendations).
DuckDB queries the uploaded CSV/Parquet files directly from disk, which
avoids an ETL step and is dramatically faster for the kind of ad-hoc
columnar aggregation EDA/KPI computation needs.

This module is not used by anything yet in Module 1 -- it exists now so
the Ingestion module (Module 3) has a ready-made, already-reviewed
pattern to build on instead of inventing DuckDB access ad hoc.
"""
import os
from contextlib import contextmanager
from pathlib import Path

import duckdb

from app.core.config import settings


def ensure_duckdb_dir() -> None:
    Path(settings.DUCKDB_PATH).parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_duckdb_connection():
    """
    Yields a DuckDB connection against the shared analytics file.
    Usage:
        with get_duckdb_connection() as con:
            con.execute("SELECT * FROM read_csv_auto(?)", [file_path])
    """
    ensure_duckdb_dir()
    con = duckdb.connect(database=settings.DUCKDB_PATH, read_only=False)
    try:
        yield con
    finally:
        con.close()


def query_uploaded_file(file_path: str, sql_template: str):
    """
    Convenience helper: run a SQL query directly over an uploaded file
    without loading it into memory via pandas first.

    `sql_template` must contain the placeholder `{source}`, e.g.:
        "SELECT product_id, SUM(quantity) FROM {source} GROUP BY 1"
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(file_path)

    with get_duckdb_connection() as con:
        source_expr = f"read_csv_auto('{file_path}')"
        sql = sql_template.format(source=source_expr)
        return con.execute(sql).fetchdf()
