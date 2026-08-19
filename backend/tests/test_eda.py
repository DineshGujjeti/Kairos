import io

VALID_ORDERS_CSV = (
    "order_id,product_id,quantity,unit_price\n"
    "ORD-1,PROD-1,10,25.5\n"
    "ORD-2,PROD-2,5,12.0\n"
    "ORD-3,PROD-1,7,25.5\n"
    "ORD-4,PROD-3,,40.0\n"  # deliberate missing quantity
    "ORD-5,PROD-2,500,12.0\n"  # deliberate outlier
)

SINGLE_NUMERIC_COLUMN_CSV = "order_id,product_id,quantity\nORD-1,PROD-1,10\nORD-2,PROD-2,5\n"

NO_NUMERIC_COLUMNS_CSV = "order_id,product_id\nORD-1,PROD-1\nORD-2,PROD-2\n"


def _upload(client, headers, content: str, filename="orders.csv", dataset_type="orders"):
    files = {"file": (filename, io.BytesIO(content.encode()), "text/csv")}
    data = {"dataset_type": dataset_type}
    return client.post("/api/v1/datasets/upload", files=files, data=data, headers=headers)


def _upload_and_get_id(client, headers, content: str, **kwargs) -> str:
    response = _upload(client, headers, content, **kwargs)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_eda_endpoints_require_auth(client, admin_headers):
    dataset_id = _upload_and_get_id(client, admin_headers, VALID_ORDERS_CSV)
    response = client.get(f"/api/v1/eda/{dataset_id}/preview")
    assert response.status_code == 401


def test_eda_preview(client, admin_headers):
    dataset_id = _upload_and_get_id(client, admin_headers, VALID_ORDERS_CSV)
    response = client.get(f"/api/v1/eda/{dataset_id}/preview", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["rows"] == 5
    assert body["columns"] == 4
    assert "order_id" in body["column_names"]
    assert len(body["sample_rows"]) == 5


def test_eda_summary(client, admin_headers):
    dataset_id = _upload_and_get_id(client, admin_headers, VALID_ORDERS_CSV)
    response = client.get(f"/api/v1/eda/{dataset_id}/summary", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["rows"] == 5
    assert body["numeric_columns"] == 2  # quantity, unit_price


def test_eda_statistics(client, admin_headers):
    dataset_id = _upload_and_get_id(client, admin_headers, VALID_ORDERS_CSV)
    response = client.get(f"/api/v1/eda/{dataset_id}/statistics", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total_numeric_columns"] == 2
    assert "quantity" in body["columns"]
    # percentile keys must round-trip through the alias correctly
    assert "25%" in body["columns"]["quantity"]
    assert "mean" in body["columns"]["quantity"]


def test_eda_missing_values(client, admin_headers):
    dataset_id = _upload_and_get_id(client, admin_headers, VALID_ORDERS_CSV)
    response = client.get(f"/api/v1/eda/{dataset_id}/missing-values", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["dataset"]["total_missing_cells"] == 1
    assert "quantity" in body["summary"]["missing_columns"]
    assert body["columns"]["quantity"]["missing_count"] == 1
    assert body["columns"]["order_id"]["is_complete"] is True


def test_eda_correlation_normal_case(client, admin_headers):
    dataset_id = _upload_and_get_id(client, admin_headers, VALID_ORDERS_CSV)
    response = client.get(f"/api/v1/eda/{dataset_id}/correlation", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total_numeric_columns"] == 2
    assert "threshold" in body
    assert "quantity" in body["correlation_matrix"]


def test_eda_correlation_with_fewer_than_two_numeric_columns(client, admin_headers):
    """Regression test for the branch-inconsistency fix: the <2-numeric-column
    path must still include 'threshold' or response validation fails."""
    dataset_id = _upload_and_get_id(
        client, admin_headers, SINGLE_NUMERIC_COLUMN_CSV, filename="single.csv"
    )
    response = client.get(f"/api/v1/eda/{dataset_id}/correlation", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total_numeric_columns"] == 1
    assert body["threshold"] == 0.8
    assert body["correlation_matrix"] == {}


def test_eda_outliers_detects_injected_outlier(client, admin_headers):
    dataset_id = _upload_and_get_id(client, admin_headers, VALID_ORDERS_CSV)
    response = client.get(f"/api/v1/eda/{dataset_id}/outliers", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total_outliers"] >= 1
    assert "quantity" in body["column_names_with_outliers"]


def test_eda_outliers_with_no_numeric_columns(client, admin_headers):
    """Regression test for the branch-inconsistency fix: the no-numeric-column
    path must still include all summary keys or response validation fails."""
    dataset_id = _upload_and_get_id(
        client, admin_headers, NO_NUMERIC_COLUMNS_CSV, filename="no_numeric.csv"
    )
    response = client.get(f"/api/v1/eda/{dataset_id}/outliers", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total_numeric_columns"] == 0
    assert body["columns_with_outliers"] == 0
    assert body["column_names_with_outliers"] == []
    assert body["total_outliers"] == 0


def test_eda_distribution(client, admin_headers):
    dataset_id = _upload_and_get_id(client, admin_headers, VALID_ORDERS_CSV)
    response = client.get(f"/api/v1/eda/{dataset_id}/distribution", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert "quantity" in body["columns"]
    assert "skewness" in body["columns"]["quantity"]


def test_eda_quality_score(client, admin_headers):
    dataset_id = _upload_and_get_id(client, admin_headers, VALID_ORDERS_CSV)
    response = client.get(f"/api/v1/eda/{dataset_id}/quality", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert 0 <= body["quality_score"] <= 100
    assert body["rating"] in ("Excellent", "Good", "Fair", "Poor")
    assert body["metrics"]["completeness"] < 100  # we injected a missing value


def test_eda_insights_flags_missing_value(client, admin_headers):
    dataset_id = _upload_and_get_id(client, admin_headers, VALID_ORDERS_CSV)
    response = client.get(f"/api/v1/eda/{dataset_id}/insights", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total_insights"] >= 1
    assert any("missing" in insight.lower() for insight in body["insights"])


def test_eda_unified_report_contains_all_sections(client, admin_headers):
    dataset_id = _upload_and_get_id(client, admin_headers, VALID_ORDERS_CSV)
    response = client.get(f"/api/v1/eda/{dataset_id}/report", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    for section in (
        "preview",
        "summary",
        "statistics",
        "missing_values",
        "correlation",
        "outliers",
        "distribution",
        "quality",
        "insights",
    ):
        assert section in body


def test_eda_returns_404_for_nonexistent_dataset(client, admin_headers):
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/api/v1/eda/{fake_id}/preview", headers=admin_headers)
    assert response.status_code == 404


def test_eda_returns_404_for_dataset_in_other_org(client, admin_headers, other_org_headers):
    dataset_id = _upload_and_get_id(client, admin_headers, VALID_ORDERS_CSV)
    response = client.get(f"/api/v1/eda/{dataset_id}/preview", headers=other_org_headers)
    assert response.status_code == 404


def test_eda_accessible_to_viewer_role(client, admin_headers, viewer_headers):
    """EDA/read endpoints are analysis, not upload/delete -- Viewer role
    should be able to run them, matching the read-permission pattern
    already established for dataset list/get/preview in Module 2."""
    dataset_id = _upload_and_get_id(client, admin_headers, VALID_ORDERS_CSV)
    response = client.get(f"/api/v1/eda/{dataset_id}/summary", headers=viewer_headers)
    assert response.status_code == 200
