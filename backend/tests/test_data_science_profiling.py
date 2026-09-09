"""Profiling + dataset classification (master spec §7 / §53)."""

import pandas as pd
import pytest

from app.data_science.dataset import ColumnKind, Dataset, classify_column
from app.data_science.profiling import profile_dataset


@pytest.fixture
def messy_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id": list(range(1, 11)),
            "age": [25, 30, None, 45, 50, 22, 38, 41, 29, 33],
            "city": ["Delhi", "delhi", "DELHI", "Mumbai", "Mumbai", "Delhi", "Pune", "Pune", "Delhi", "Mumbai"],
            "active": [True, False, True, True, False, True, False, True, True, False],
            "signup": pd.to_datetime(
                ["2024-01-01", "2024-01-05", "2024-02-01", "2024-02-15", "2024-03-01",
                 "2024-03-10", "2024-04-01", "2024-04-15", "2024-05-01", "2024-05-10"]
            ),
            "constant": ["x"] * 10,
            "salary": [40000, 42000, 44000, 43000, 999999, 41000, 45000, 46000, 42000, 43000],
        }
    )


def test_column_classification(messy_df):
    ds = Dataset.from_records(messy_df.columns, messy_df.to_dict("records"))
    kinds = ds.column_kinds()
    assert kinds["age"] == ColumnKind.NUMERIC
    assert kinds["city"] == ColumnKind.CATEGORICAL
    assert kinds["active"] == ColumnKind.BOOLEAN
    assert kinds["signup"] == ColumnKind.DATETIME
    assert kinds["salary"] == ColumnKind.NUMERIC


def test_dataset_level_profile_counts(messy_df):
    ds = Dataset.from_records(messy_df.columns, messy_df.to_dict("records"))
    prof = profile_dataset(ds)["dataset"]
    assert prof["n_rows"] == 10
    assert prof["n_cols"] == 7
    assert prof["missing_cells"] == 1  # one missing age
    assert "constant" in prof["constant_columns"]
    assert prof["duplicate_rows"] == 0


def test_column_level_stats_are_computed_not_estimated(messy_df):
    ds = Dataset.from_records(messy_df.columns, messy_df.to_dict("records"))
    cols = {c["name"]: c for c in profile_dataset(ds)["columns"]}
    age = cols["age"]
    assert age["missing"] == 1
    assert age["count"] == 9
    # mean/median computed from the 9 present values
    present = [25, 30, 45, 50, 22, 38, 41, 29, 33]
    assert age["mean"] == pytest.approx(sum(present) / len(present), rel=1e-6)
    salary = cols["salary"]
    assert salary["outlier_count"] >= 1  # 999999 is an IQR outlier
    assert salary["max"] == 999999


def test_duplicate_detection():
    df = pd.DataFrame({"a": [1, 1, 2, 3], "b": ["x", "x", "y", "z"]})
    ds = Dataset.from_records(df.columns, df.to_dict("records"))
    assert profile_dataset(ds)["dataset"]["duplicate_rows"] == 2


def test_high_cardinality_flag():
    df = pd.DataFrame({"token": [f"tok-{i}" for i in range(200)]})
    ds = Dataset.from_records(df.columns, df.to_dict("records"))
    prof = profile_dataset(ds)["dataset"]
    assert "token" in prof["high_cardinality_columns"]


def test_empty_column_is_empty_kind():
    assert classify_column(pd.Series([None, None, None])) == ColumnKind.EMPTY


def test_row_cap_samples_large_datasets():
    df = pd.DataFrame({"x": range(60_000)})
    ds = Dataset.from_records(df.columns, df.to_dict("records"))
    assert ds.sampled is True
    assert ds.n_rows == 50_000
    assert ds.original_row_count == 60_000
