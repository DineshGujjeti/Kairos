# ADR-0001: Use PostgreSQL for transactional state and DuckDB for analytical queries

**Status:** Accepted
**Date:** 2026-07-12

## Context

Kairos needs to (a) store application/transactional state (users,
organizations, dataset metadata, model runs, recommendations) reliably
with ACID guarantees, and (b) run fast ad-hoc analytical aggregations
over uploaded CSV/Parquet datasets that can be large and arrive with
inconsistent schemas.

## Decision

PostgreSQL is the system of record for all transactional/application
state. DuckDB queries uploaded dataset files directly from disk for
analytical workloads (EDA, KPI computation) -- raw dataset rows are
never loaded into Postgres.

## Consequences

- **Positive:** no ETL step between upload and analysis; DuckDB's
  columnar engine is dramatically faster than row-store Postgres for
  the group-by/aggregate-heavy queries EDA and KPI generation need;
  Postgres stays small and fast since it only holds metadata and
  derived results.
- **Negative:** two query engines to reason about instead of one; the
  team (i.e., future-you) must remember the rule "raw rows live in
  files, queried by DuckDB; derived/application state lives in
  Postgres" and not blur the line by convenience-dumping rows into
  Postgres later.
- **Alternatives considered:** Postgres alone (rejected -- would
  require either loading every uploaded file into Postgres tables via
  ETL, adding latency and schema-migration overhead per dataset, or
  running slow analytical queries on a row store). A single
  Postgres-with-columnar-extension setup was also considered but adds
  operational complexity without DuckDB's simplicity of "just point it
  at a file."

---

*New ADRs go in this folder as `NNNN-short-title.md`, numbered
sequentially. An ADR is written when a decision is non-obvious, has
real tradeoffs, or would confuse a future contributor (or an examiner)
if left unexplained -- not for routine implementation details.*
