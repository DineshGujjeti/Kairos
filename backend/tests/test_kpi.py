import io
import pytest

NUMERIC_CSV = (
    "product_id,revenue,cost,quantity,date\n"
    "PROD-1,1000,400,100,2024-01-01\n"
    "PROD-2,1500,600,150,2024-02-01\n"
    "PROD-1,800,300,80,2024-03-01\n"
    "PROD-3,2000,800,200,2024-04-01\n"
    "PROD-2,,500,120,2024-05-01\n"  # missing revenue
    "PROD-1,900,400,90,2024-06-01\n"
)


def _upload_csv(client, headers, content: str, filename="data.csv"):
    files = {"file": (filename, io.BytesIO(content.encode()), "text/csv")}
    data = {"dataset_type": "orders"}
    response = client.post("/api/v1/datasets/upload", files=files, data=data, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_kpi_overview(client, admin_headers):
    dataset_id = _upload_csv(client, admin_headers, NUMERIC_CSV)
    response = client.get(f"/api/v1/kpi/{dataset_id}/overview", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["rows"] == 6
    assert body["columns"] == 5
    assert body["numeric_columns"] == 3


def test_kpi_metrics(client, admin_headers):
    dataset_id = _upload_csv(client, admin_headers, NUMERIC_CSV)
    response = client.get(f"/api/v1/kpi/{dataset_id}/metrics", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total_numeric_columns"] == 3
    assert "revenue" in body["columns"]
    assert body["columns"]["revenue"]["count"] == 5  # one missing value
    assert body["columns"]["revenue"]["mean"] is not None


def test_kpi_ranking(client, admin_headers):
    dataset_id = _upload_csv(client, admin_headers, NUMERIC_CSV)
    response = client.get(
        f"/api/v1/kpi/{dataset_id}/ranking",
        params={"dimension": "product_id", "metric": "revenue", "top_n": 3},
        headers=admin_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["dimension"] == "product_id"
    assert body["metric"] == "revenue"
    assert len(body["items"]) <= 3
    assert body["total_groups"] >= 1


def test_kpi_ranking_invalid_column(client, admin_headers):
    dataset_id = _upload_csv(client, admin_headers, NUMERIC_CSV)
    response = client.get(
        f"/api/v1/kpi/{dataset_id}/ranking",
        params={"dimension": "nonexistent", "metric": "revenue"},
        headers=admin_headers,
    )
    assert response.status_code == 404


def test_kpi_ranking_invalid_metric_type(client, admin_headers):
    dataset_id = _upload_csv(client, admin_headers, NUMERIC_CSV)
    response = client.get(
        f"/api/v1/kpi/{dataset_id}/ranking",
        params={"dimension": "product_id", "metric": "product_id"},
        headers=admin_headers,
    )
    assert response.status_code == 422


def test_kpi_trend_auto_detect_datetime(client, admin_headers):
    dataset_id = _upload_csv(client, admin_headers, NUMERIC_CSV)
    response = client.get(
        f"/api/v1/kpi/{dataset_id}/trend",
        params={"metric": "revenue", "frequency": "monthly"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["has_datetime_column"] is True
    assert body["datetime_column_used"] is not None
    assert body["frequency"] == "monthly"
    assert len(body["points"]) > 0


def test_kpi_trend_no_datetime(client, admin_headers):
    no_date_csv = "product_id,revenue,cost\nPROD-1,1000,400\nPROD-2,1500,600\n"
    dataset_id = _upload_csv(client, admin_headers, no_date_csv)
    response = client.get(
        f"/api/v1/kpi/{dataset_id}/trend",
        params={"metric": "revenue"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["has_datetime_column"] is False
    assert body["points"] == []


def test_kpi_dashboard(client, admin_headers):
    dataset_id = _upload_csv(client, admin_headers, NUMERIC_CSV)
    response = client.get(f"/api/v1/kpi/{dataset_id}/dashboard", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert "overview" in body
    assert "metrics" in body
    assert "alerts" in body
    assert "timestamp" in body


def test_kpi_alerts(client, admin_headers):
    dataset_id = _upload_csv(client, admin_headers, NUMERIC_CSV)
    response = client.get(f"/api/v1/kpi/{dataset_id}/alerts", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert "total_alerts" in body
    assert "alerts" in body
    assert isinstance(body["alerts"], list)


def test_kpi_formula_simple(client, admin_headers):
    dataset_id = _upload_csv(client, admin_headers, NUMERIC_CSV)
    response = client.post(
        f"/api/v1/kpi/{dataset_id}/formula",
        json={"formula": "revenue - cost"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["formula"] == "revenue - cost"
    assert body["result_type"] == "series"


def test_kpi_formula_invalid_column(client, admin_headers):
    dataset_id = _upload_csv(client, admin_headers, NUMERIC_CSV)
    response = client.post(
        f"/api/v1/kpi/{dataset_id}/formula",
        json={"formula": "nonexistent_col * 2"},
        headers=admin_headers,
    )
    assert response.status_code == 404


def test_kpi_formula_dangerous(client, admin_headers):
    dataset_id = _upload_csv(client, admin_headers, NUMERIC_CSV)
    # __import__ contains __ which is blocked
    response = client.post(
        f"/api/v1/kpi/{dataset_id}/formula",
        json={"formula": "__import__('os')"},
        headers=admin_headers,
    )
    assert response.status_code == 422


def test_kpi_requires_auth(client, admin_headers):
    dataset_id = _upload_csv(client, admin_headers, NUMERIC_CSV)
    response = client.get(f"/api/v1/kpi/{dataset_id}/overview")
    assert response.status_code == 401


def test_kpi_cross_org_isolation(client, admin_headers, other_org_headers):
    dataset_id = _upload_csv(client, admin_headers, NUMERIC_CSV)
    response = client.get(
        f"/api/v1/kpi/{dataset_id}/overview",
        headers=other_org_headers,
    )
    assert response.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# Smart KPI Cards -- curated, business-readable metrics endpoint
# ─────────────────────────────────────────────────────────────────────────────

LARGER_SALES_CSV = "date,revenue,discount_rate\n" + "".join(
    f"2024-{(i // 28) + 1:02d}-{(i % 28) + 1:02d},{1000 + i * 25},{5 + (i % 10) * 0.3}\n"
    for i in range(40)
)


def test_smart_kpi_cards_returns_200(client, admin_headers):
    dataset_id = _upload_csv(client, admin_headers, LARGER_SALES_CSV)
    response = client.get(f"/api/v1/kpi/{dataset_id}/smart-cards", headers=admin_headers)
    assert response.status_code == 200


def test_smart_kpi_cards_schema(client, admin_headers):
    dataset_id = _upload_csv(client, admin_headers, LARGER_SALES_CSV)
    body = client.get(f"/api/v1/kpi/{dataset_id}/smart-cards", headers=admin_headers).json()
    assert "cards" in body
    assert "has_measures" in body
    assert "has_time_comparison" in body
    assert "summary" in body
    assert body["has_measures"] is True
    assert body["has_time_comparison"] is True
    for card in body["cards"]:
        assert "label" in card
        assert "formatted_value" in card
        assert "description" in card
        assert "direction" in card
        assert card["direction"] in ("up", "down", "flat")
        assert "sentiment" in card
        assert card["sentiment"] in ("positive", "negative", "neutral")


def test_smart_kpi_cards_max_cards_param(client, admin_headers):
    dataset_id = _upload_csv(client, admin_headers, LARGER_SALES_CSV)
    response = client.get(f"/api/v1/kpi/{dataset_id}/smart-cards?max_cards=1", headers=admin_headers)
    assert response.status_code == 200
    assert len(response.json()["cards"]) <= 1


def test_smart_kpi_cards_no_numeric_columns_graceful(client, admin_headers):
    csv = "name,category\n" + "".join(f"item-{i},cat-{i % 3}\n" for i in range(10))
    dataset_id = _upload_csv(client, admin_headers, csv)
    response = client.get(f"/api/v1/kpi/{dataset_id}/smart-cards", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["has_measures"] is False
    assert body["cards"] == []


def test_smart_kpi_cards_requires_auth(client, admin_headers):
    dataset_id = _upload_csv(client, admin_headers, LARGER_SALES_CSV)
    response = client.get(f"/api/v1/kpi/{dataset_id}/smart-cards")
    assert response.status_code == 401


def test_smart_kpi_cards_cross_org_isolation(client, admin_headers, other_org_headers):
    dataset_id = _upload_csv(client, admin_headers, LARGER_SALES_CSV)
    response = client.get(f"/api/v1/kpi/{dataset_id}/smart-cards", headers=other_org_headers)
    assert response.status_code == 404
