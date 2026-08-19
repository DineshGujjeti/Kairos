"""
Tests for app.services.dataset_intelligence -- the dynamic, dataset-agnostic
column profiler used to make every module work with any uploaded dataset
(not just the six built-in supply-chain categories).
"""
import pandas as pd

from app.services.dataset_intelligence import profile_dataset


def test_empty_dataframe_never_raises():
    result = profile_dataset(pd.DataFrame())
    assert result["row_count"] == 0
    assert result["columns"] == {}
    assert result["best_datetime_column"] is None
    assert result["target_candidates"] == []


def test_single_constant_column():
    df = pd.DataFrame({"flag": [1, 1, 1, 1]})
    result = profile_dataset(df)
    assert result["roles"] == {"constant": ["flag"]}


def test_hr_dataset_detects_roles_dynamically():
    df = pd.DataFrame({
        "employee_id": range(1, 41),
        "full_name": [f"Person {i}" for i in range(40)],
        "department": (["Engineering", "Sales", "HR", "Finance"] * 10),
        "hire_date": pd.date_range("2019-01-01", periods=40, freq="30D").astype(str),
        "salary": [50000 + i * 1000 for i in range(40)],
        "attrition": (["Yes", "No"] * 20),
    })
    result = profile_dataset(df)

    assert "employee_id" in result["roles"].get("id", [])
    assert "department" in result["roles"].get("categorical_dimension", [])
    assert "hire_date" in result["roles"].get("datetime", [])
    assert "salary" in result["roles"].get("numeric_measure", [])
    assert "attrition" in result["roles"].get("boolean", [])
    assert result["best_datetime_column"] == "hire_date"
    assert "salary" in result["target_candidates"]
    assert result["domain_guess"] == "Human Resources"


def test_healthcare_dataset_domain_guess():
    df = pd.DataFrame({
        "patient_id": range(1, 31),
        "diagnosis": (["Flu", "Diabetes", "Hypertension"] * 10),
        "admission_date": pd.date_range("2023-01-01", periods=30, freq="7D").astype(str),
        "treatment_cost": [200 + i * 15 for i in range(30)],
        "physician": [f"Dr. {i % 5}" for i in range(30)],
    })
    result = profile_dataset(df)
    assert result["domain_guess"] == "Healthcare"
    assert "patient_id" in result["roles"].get("id", [])
    assert "treatment_cost" in result["target_candidates"]


def test_iot_sensor_dataset_no_business_naming():
    df = pd.DataFrame({
        "device_uuid": [f"dev-{i}" for i in range(30)],
        "reading_ts": pd.date_range("2024-06-01", periods=30, freq="h").astype(str),
        "temperature": [20 + (i % 5) * 0.5 for i in range(30)],
        "status": (["ok", "warn"] * 15),
    })
    result = profile_dataset(df)
    assert result["best_datetime_column"] == "reading_ts"
    assert "device_uuid" in result["roles"].get("id", [])
    assert "temperature" in result["target_candidates"]


def test_generic_dataset_with_no_domain_keywords_gets_general_label():
    df = pd.DataFrame({
        "colA": range(20),
        "colB": [f"val-{i}" for i in range(20)],
    })
    result = profile_dataset(df)
    assert result["domain_guess"] == "General Business Data"


def test_numeric_id_column_not_treated_as_measure():
    df = pd.DataFrame({
        "record_id": range(1, 51),  # sequential, unique, id-like name
        "amount": [i * 3.3 for i in range(50)],
    })
    result = profile_dataset(df)
    assert "record_id" in result["roles"].get("id", [])
    assert "amount" in result["target_candidates"]


def test_free_text_column_detected_not_categorical():
    df = pd.DataFrame({
        "notes": [f"This is a unique free-form note number {i} about something." for i in range(30)],
        "amount": range(30),
    })
    result = profile_dataset(df)
    assert "notes" in result["roles"].get("free_text", [])


def test_profile_never_raises_on_all_null_column():
    df = pd.DataFrame({"empty_col": [None, None, None], "amount": [1, 2, 3]})
    result = profile_dataset(df)
    assert "empty_col" in result["columns"]


def test_primary_dimensions_ranked_by_cardinality():
    df = pd.DataFrame({
        "region": (["North", "South"] * 15),           # 2 unique / 30 rows
        "segment": (["A", "B", "C", "D", "E"] * 6),      # 5 unique / 30 rows
        "amount": range(30),
    })
    result = profile_dataset(df)
    # Lower cardinality ratio should be ranked first
    assert result["primary_dimensions"][0] == "region"
