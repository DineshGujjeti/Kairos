"""
Module 4: Enterprise KPI & Dashboard Engine.

Each file in this package is a single-responsibility unit (SRP):
loader (dataset -> DataFrame), calculator (per-column metrics),
overview (dataset-level shape), ranking (group-by top-N), trend
(time-series aggregation), alerts (rule-based data-quality signals),
formula (safe user-defined expressions), and dashboard (orchestrates
all of the above into one payload). Routes stay thin and only call
into these -- no business logic lives in app/api/v1/kpi/routes.py.
"""
