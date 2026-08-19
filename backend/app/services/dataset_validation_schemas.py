"""
Structural validation schemas, one per DatasetType.

Scope discipline matters here: these schemas check "does this file
look like the kind of dataset it claims to be" (required columns
present, id-like columns non-null, basic dtype sanity) -- NOT data
quality (null rates, outliers, distributions), which is Module 3's
job (Automated EDA). Keeping that boundary sharp is what stops Module
2 from quietly growing into Module 3.

These are intentionally starter schemas covering the columns any real
supply-chain export of each type would be expected to have. They are
easy to extend per-column as later modules (KPI engine, forecasting)
reveal more specific requirements -- extending a Pandera schema is a
small, local diff, not a rewrite.
"""
import pandera as pa
from pandera import Column, DataFrameSchema

from app.db.models.dataset import DatasetType

_orders_schema = DataFrameSchema(
    {
        "order_id": Column(str, coerce=True, nullable=False),
        "product_id": Column(str, coerce=True, nullable=False),
        "quantity": Column(pa.Float, coerce=True, nullable=False, checks=pa.Check.ge(0)),
    },
    strict=False,  # extra columns are allowed; we only enforce the required core
)

_products_schema = DataFrameSchema(
    {
        "product_id": Column(str, coerce=True, nullable=False),
        "product_name": Column(str, coerce=True, nullable=False),
    },
    strict=False,
)

_inventory_schema = DataFrameSchema(
    {
        "product_id": Column(str, coerce=True, nullable=False),
        "warehouse_id": Column(str, coerce=True, nullable=False),
        "quantity_on_hand": Column(pa.Float, coerce=True, nullable=False, checks=pa.Check.ge(0)),
    },
    strict=False,
)

_warehouses_schema = DataFrameSchema(
    {
        "warehouse_id": Column(str, coerce=True, nullable=False),
        "warehouse_name": Column(str, coerce=True, nullable=False),
    },
    strict=False,
)

_suppliers_schema = DataFrameSchema(
    {
        "supplier_id": Column(str, coerce=True, nullable=False),
        "supplier_name": Column(str, coerce=True, nullable=False),
    },
    strict=False,
)

_deliveries_schema = DataFrameSchema(
    {
        "delivery_id": Column(str, coerce=True, nullable=False),
        "order_id": Column(str, coerce=True, nullable=False),
    },
    strict=False,
)

SCHEMA_REGISTRY: dict[DatasetType, DataFrameSchema] = {
    DatasetType.ORDERS: _orders_schema,
    DatasetType.PRODUCTS: _products_schema,
    DatasetType.INVENTORY: _inventory_schema,
    DatasetType.WAREHOUSES: _warehouses_schema,
    DatasetType.SUPPLIERS: _suppliers_schema,
    DatasetType.DELIVERIES: _deliveries_schema,
}


def get_schema_for(dataset_type: DatasetType) -> DataFrameSchema | None:
    """
    Returns the structural Pandera schema for known supply-chain dataset
    types, or None for GENERAL -- callers must treat None as "skip
    structural validation, this dataset is domain-agnostic and gets
    profiled dynamically instead" (see dataset_intelligence.py).
    """
    if dataset_type == DatasetType.GENERAL:
        return None
    return SCHEMA_REGISTRY[dataset_type]
