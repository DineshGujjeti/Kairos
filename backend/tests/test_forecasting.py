"""Tests for Module 5: Forecasting Engine with improved schema."""
import io

TIMESERIES_CSV = (
    "date,sales\n"
    "2024-01-01,1000\n"
    "2024-01-02,1100\n"
    "2024-01-03,900\n"
    "2024-01-04,1200\n"
    "2024-01-05,1050\n"
    "2024-01-06,1300\n"
    "2024-01-07,1150\n"
    "2024-01-08,1250\n"
    "2024-01-09,1100\n"
    "2024-01-10,1400\n"
    "2024-01-11,1200\n"
    "2024-01-12,1350\n"
    "2024-01-13,1150\n"
    "2024-01-14,1500\n"
    "2024-01-15,1300\n"
    "2024-01-16,1450\n"
    "2024-01-17,1200\n"
    "2024-01-18,1550\n"
    "2024-01-19,1350\n"
    "2024-01-20,1600\n"
    "2024-01-21,1400\n"
    "2024-01-22,1700\n"
    "2024-01-23,1500\n"
    "2024-01-24,1750\n"
    "2024-01-25,1550\n"
    "2024-01-26,1800\n"
    "2024-01-27,1600\n"
    "2024-01-28,1850\n"
    "2024-01-29,1650\n"
    "2024-01-30,1900\n"
)


def _upload_timeseries(client, headers, content: str = TIMESERIES_CSV):
    files = {"file": ("timeseries.csv", io.BytesIO(content.encode()), "text/csv")}
    data = {"dataset_type": "orders"}
    response = client.post("/api/v1/datasets/upload", files=files, data=data, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_forecasting_requires_auth(client, admin_headers):
    dataset_id = _upload_timeseries(client, admin_headers)
    response = client.get(f"/api/v1/forecasting/{dataset_id}/overview")
    assert response.status_code == 401


def test_forecast_overview(client, admin_headers):
    dataset_id = _upload_timeseries(client, admin_headers)
    response = client.get(f"/api/v1/forecasting/{dataset_id}/overview", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["rows"] == 30
    assert body["datetime_column"] == "date"
    assert body["target_column"] == "sales"
    assert "datetime_auto_detected" in body
    assert "target_auto_detected" in body
    assert "date_range_start" in body


def test_forecast_overview_manual_columns(client, admin_headers):
    dataset_id = _upload_timeseries(client, admin_headers)
    response = client.get(
        f"/api/v1/forecasting/{dataset_id}/overview?datetime_column=date&target_column=sales",
        headers=admin_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["datetime_column"] == "date"
    assert body["target_column"] == "sales"
    assert body["datetime_auto_detected"] is False
    assert body["target_auto_detected"] is False


def test_train_forecast_model(client, admin_headers):
    dataset_id = _upload_timeseries(client, admin_headers)
    response = client.post(
        f"/api/v1/forecasting/{dataset_id}/forecast",
        json={"periods": 7},
        headers=admin_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert "selected_model" in body
    assert body["selected_model"] in ("Prophet", "Linear Regression", "Moving Average")
    assert len(body["forecast_dates"]) == 7
    assert len(body["forecast_values"]) == 7
    assert "training_metrics" in body
    assert "confidence_intervals" in body
    assert "detected_datetime_column" in body
    assert "detected_target_column" in body
    assert len(body["historical_dates"]) == 30
    assert len(body["historical_values"]) == 30


def test_analyze_time_series(client, admin_headers):
    dataset_id = _upload_timeseries(client, admin_headers)
    response = client.get(
        f"/api/v1/forecasting/{dataset_id}/analysis",
        headers=admin_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["datetime_column"] == "date"
    assert body["target_column"] == "sales"
    assert "trend" in body
    assert "seasonality" in body
    assert body["trend"]["direction"] in ("increasing", "decreasing", "stable")
    assert "is_seasonal" in body["seasonality"]


def test_complete_forecast_report(client, admin_headers):
    dataset_id = _upload_timeseries(client, admin_headers)
    response = client.post(
        f"/api/v1/forecasting/{dataset_id}/report",
        json={"periods": 14},
        headers=admin_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert "overview" in body
    assert "analysis" in body
    assert "forecast" in body
    assert "selected_model" in body["forecast"]
    assert body["forecast"]["selected_model"] in ("Prophet", "Linear Regression", "Moving Average")
    assert len(body["forecast"]["forecast_dates"]) == 14


def test_forecast_no_datetime_and_too_few_rows_is_graceful(client, admin_headers):
    """
    No date column AND too few rows (2 < 10) for even a synthetic
    row-order fallback -- forecasting genuinely isn't possible here, but
    the API must degrade gracefully (HTTP 200, available=False) rather
    than crash with a bare 422. See detector.safe_validate_for_forecasting.
    """
    no_datetime_csv = "product_id,sales\nPROD-1,1000\nPROD-2,1100\n"
    dataset_id = _upload_timeseries(client, admin_headers, no_datetime_csv)
    response = client.get(
        f"/api/v1/forecasting/{dataset_id}/overview",
        headers=admin_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["unavailable_reason"]


def test_forecast_no_datetime_but_enough_rows_uses_synthetic_fallback(client, admin_headers):
    """
    No date column, but enough rows and a real numeric measure -- must
    NOT give up. Forecasting proceeds using row order as a synthetic
    time axis instead of failing outright.
    """
    csv = "product_id,units_sold\n" + "".join(
        f"PROD-{i},{100 + i * 5}\n" for i in range(20)
    )
    dataset_id = _upload_timeseries(client, admin_headers, csv)
    response = client.get(
        f"/api/v1/forecasting/{dataset_id}/overview",
        headers=admin_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert body["synthetic_datetime"] is True
    assert body["target_column"] == "units_sold"


def test_forecast_insufficient_data_is_graceful(client, admin_headers):
    """A real date column but too few rows (3 < 10) must also degrade
    gracefully rather than 422."""
    small_data_csv = "date,sales\n2024-01-01,100\n2024-01-02,110\n2024-01-03,120\n"
    dataset_id = _upload_timeseries(client, admin_headers, small_data_csv)
    response = client.get(
        f"/api/v1/forecasting/{dataset_id}/overview",
        headers=admin_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["unavailable_reason"]


def test_forecast_report_end_to_end_with_synthetic_datetime(client, admin_headers):
    """The combined /report endpoint must also work end-to-end on a
    dateless-but-forecastable dataset, using the same synthetic column
    consistently across its overview/analysis/forecast sections."""
    csv = "employee_id,headcount_change\n" + "".join(
        f"{i},{5 + (i % 4) - 2}\n" for i in range(25)
    )
    dataset_id = _upload_timeseries(client, admin_headers, csv)
    response = client.post(
        f"/api/v1/forecasting/{dataset_id}/report",
        json={"periods": 5},
        headers=admin_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert body["overview"]["synthetic_datetime"] is True
    assert body["forecast"]["synthetic_datetime"] is True
    assert len(body["forecast"]["forecast_values"]) == 5


def test_forecast_cross_org_isolation(client, admin_headers, other_org_headers):
    dataset_id = _upload_timeseries(client, admin_headers)
    response = client.get(
        f"/api/v1/forecasting/{dataset_id}/overview",
        headers=other_org_headers,
    )
    assert response.status_code == 404


def test_forecast_nonexistent_dataset(client, admin_headers):
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.get(
        f"/api/v1/forecasting/{fake_id}/overview",
        headers=admin_headers,
    )
    assert response.status_code == 404
