import io

import pytest

VALID_ORDERS_CSV = (
    "order_id,product_id,quantity\n"
    "ORD-1,PROD-1,10\n"
    "ORD-2,PROD-2,5\n"
    "ORD-3,PROD-1,7\n"
)

INVALID_ORDERS_CSV = (
    "order_id,quantity\n"  # missing required product_id column
    "ORD-1,10\n"
)

EMPTY_CSV = ""


def _upload(client, headers, content: str, filename="orders.csv", dataset_type="orders", name=None):
    files = {"file": (filename, io.BytesIO(content.encode()), "text/csv")}
    data = {"dataset_type": dataset_type}
    if name:
        data["name"] = name
    return client.post(
        "/api/v1/datasets/upload", files=files, data=data, headers=headers
    )


def test_upload_valid_csv_succeeds(client, admin_headers):
    response = _upload(client, admin_headers, VALID_ORDERS_CSV)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "valid"
    assert body["row_count"] == 3
    assert body["column_count"] == 3
    assert "order_id" in body["schema_json"]
    assert body["dataset_type"] == "orders"


def test_upload_missing_required_column_marked_invalid(client, admin_headers):
    response = _upload(client, admin_headers, INVALID_ORDERS_CSV)
    assert response.status_code == 201  # upload itself succeeds, validity is a status field
    body = response.json()
    assert body["status"] == "invalid"
    assert body["validation_errors"] is not None


def test_upload_empty_file_rejected(client, admin_headers):
    response = _upload(client, admin_headers, EMPTY_CSV)
    assert response.status_code == 422


def test_upload_unsupported_extension_rejected(client, admin_headers):
    response = _upload(client, admin_headers, VALID_ORDERS_CSV, filename="orders.txt")
    assert response.status_code == 415


def test_upload_rejected_for_viewer_role(client, viewer_headers):
    response = _upload(client, viewer_headers, VALID_ORDERS_CSV)
    assert response.status_code == 403


def test_upload_rejected_without_auth(client):
    files = {"file": ("orders.csv", io.BytesIO(VALID_ORDERS_CSV.encode()), "text/csv")}
    response = client.post(
        "/api/v1/datasets/upload", files=files, data={"dataset_type": "orders"}
    )
    assert response.status_code == 401


def test_list_datasets_scoped_to_org(client, admin_headers, other_org_headers):
    _upload(client, admin_headers, VALID_ORDERS_CSV, name="mine")

    mine = client.get("/api/v1/datasets", headers=admin_headers)
    assert mine.status_code == 200
    assert mine.json()["total"] == 1

    other = client.get("/api/v1/datasets", headers=other_org_headers)
    assert other.status_code == 200
    assert other.json()["total"] == 0  # cross-org isolation


def test_get_dataset_by_id(client, admin_headers):
    upload_response = _upload(client, admin_headers, VALID_ORDERS_CSV)
    dataset_id = upload_response.json()["id"]

    response = client.get(f"/api/v1/datasets/{dataset_id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["id"] == dataset_id


def test_get_dataset_from_other_org_returns_404(client, admin_headers, other_org_headers):
    upload_response = _upload(client, admin_headers, VALID_ORDERS_CSV)
    dataset_id = upload_response.json()["id"]

    response = client.get(f"/api/v1/datasets/{dataset_id}", headers=other_org_headers)
    assert response.status_code == 404


def test_preview_dataset(client, admin_headers):
    upload_response = _upload(client, admin_headers, VALID_ORDERS_CSV)
    dataset_id = upload_response.json()["id"]

    response = client.get(f"/api/v1/datasets/{dataset_id}/preview?rows=2", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["row_count_shown"] == 2
    assert body["row_count_total"] == 3
    assert "order_id" in body["columns"]


def test_delete_dataset_removes_it(client, admin_headers):
    upload_response = _upload(client, admin_headers, VALID_ORDERS_CSV)
    dataset_id = upload_response.json()["id"]

    delete_response = client.delete(f"/api/v1/datasets/{dataset_id}", headers=admin_headers)
    assert delete_response.status_code == 204

    get_response = client.get(f"/api/v1/datasets/{dataset_id}", headers=admin_headers)
    assert get_response.status_code == 404


def test_delete_rejected_for_viewer_role(client, admin_headers, viewer_headers):
    upload_response = _upload(client, admin_headers, VALID_ORDERS_CSV)
    dataset_id = upload_response.json()["id"]

    response = client.delete(f"/api/v1/datasets/{dataset_id}", headers=viewer_headers)
    assert response.status_code == 403


def test_filter_datasets_by_status(client, admin_headers):
    _upload(client, admin_headers, VALID_ORDERS_CSV, name="valid-one")
    _upload(client, admin_headers, INVALID_ORDERS_CSV, name="invalid-one")

    valid_only = client.get("/api/v1/datasets?status=valid", headers=admin_headers)
    assert valid_only.json()["total"] == 1

    invalid_only = client.get("/api/v1/datasets?status=invalid", headers=admin_headers)
    assert invalid_only.json()["total"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# GENERAL dataset type -- works with ANY dataset, no forced schema
# ─────────────────────────────────────────────────────────────────────────────

HR_CSV = (
    "employee_id,department,hire_date,salary\n"
    + "".join(
        f"{i},{'Engineering' if i % 2 == 0 else 'Sales'},2022-0{(i % 9) + 1}-01,{50000 + i * 500}\n"
        for i in range(1, 21)
    )
)


def test_dataset_type_defaults_to_general_when_omitted(client, admin_headers):
    """dataset_type is no longer a required form field -- omitting it must not 422."""
    files = {"file": ("hr.csv", io.BytesIO(HR_CSV.encode()), "text/csv")}
    response = client.post("/api/v1/datasets/upload", files=files, data={}, headers=admin_headers)
    assert response.status_code == 201, response.text
    assert response.json()["dataset_type"] == "general"


def test_general_dataset_type_never_marked_invalid_for_missing_supply_chain_columns(client, admin_headers):
    """
    An HR dataset has none of order_id/product_id/etc. Under the old
    hardcoded-schema behaviour this would be forced into one of the six
    supply-chain categories and marked INVALID. Under dataset_type=general
    it must be VALID -- there is no fixed schema to fail against.
    """
    response = _upload(client, admin_headers, HR_CSV, filename="hr.csv", dataset_type="general")
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "valid"
    assert body["validation_errors"] is None


def test_general_dataset_gets_column_profile(client, admin_headers):
    response = _upload(client, admin_headers, HR_CSV, filename="hr.csv", dataset_type="general")
    body = response.json()
    profile = body["column_profile"]
    assert profile is not None
    assert profile["domain_guess"] == "Human Resources"
    assert "employee_id" in profile["roles"].get("id", [])
    assert "hire_date" in profile["roles"].get("datetime", [])
    assert "salary" in profile["target_candidates"]


def test_supply_chain_dataset_also_gets_column_profile(client, admin_headers):
    """Profiling runs for every dataset_type, not just GENERAL."""
    response = _upload(client, admin_headers, VALID_ORDERS_CSV)
    body = response.json()
    assert body["column_profile"] is not None
    assert body["column_profile"]["row_count"] == 3


def test_dataset_list_includes_domain_guess(client, admin_headers):
    _upload(client, admin_headers, HR_CSV, filename="hr.csv", dataset_type="general", name="hr-data")
    listing = client.get("/api/v1/datasets", headers=admin_headers).json()
    item = next(i for i in listing["items"] if i["name"] == "hr-data")
    assert item["domain_guess"] == "Human Resources"


def test_general_dataset_flows_through_eda(client, admin_headers):
    """An HR dataset (no supply-chain columns) must work in EDA end-to-end."""
    upload = _upload(client, admin_headers, HR_CSV, filename="hr.csv", dataset_type="general")
    dataset_id = upload.json()["id"]
    response = client.get(f"/api/v1/eda/{dataset_id}/summary", headers=admin_headers)
    assert response.status_code == 200
