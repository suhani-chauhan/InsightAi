"""Data quality engine + explainable score (master spec §8 / §9 / §53)."""

import pandas as pd
import pytest

from app.data_science.dataset import Dataset
from app.data_science.quality import analyze_quality, quality_score


def _ds(df: pd.DataFrame) -> Dataset:
    return Dataset.from_records(df.columns, df.to_dict("records"))


def test_missing_values_detected_with_severity():
    df = pd.DataFrame({"a": [1, None, None, None, 5, 6, 7, 8, 9, 10], "b": range(10)})
    report = analyze_quality(_ds(df))
    codes = {i["code"] for i in report["issues"]}
    assert "missing::a" in codes
    issue = next(i for i in report["issues"] if i["code"] == "missing::a")
    assert issue["evidence"]["missing"] == 3
    assert issue["severity"] in ("medium", "high")


def test_completely_empty_column_recommends_drop():
    df = pd.DataFrame({"a": [None] * 8, "b": range(8)})
    report = analyze_quality(_ds(df))
    issue = next(i for i in report["issues"] if i["columns"] == ["a"])
    assert issue["suggested_operation"]["op"] == "drop_column"


def test_exact_duplicates_detected():
    df = pd.DataFrame({"a": [1, 1, 1, 2, 3], "b": ["x", "x", "x", "y", "z"]})
    report = analyze_quality(_ds(df))
    dup = next(i for i in report["issues"] if i["code"] == "duplicates::rows")
    assert dup["evidence"]["duplicate_rows"] == 3


def test_numeric_stored_as_string_flagged():
    df = pd.DataFrame({"amount": ["1,000", "2,500", "3,200", "4,100", "5,000", "6,000"]})
    report = analyze_quality(_ds(df))
    assert any(i["code"].startswith("dtype::numeric_string") for i in report["issues"])


def test_categorical_inconsistency_detected_not_merged():
    df = pd.DataFrame({"country": ["India", "india", "INDIA", "USA", "usa"] * 4})
    report = analyze_quality(_ds(df))
    issue = next(i for i in report["issues"] if i["code"].startswith("category::inconsistent"))
    # Recommends a transformation, does not auto-apply.
    assert issue["suggested_operation"]["op"] == "standardize_categories"
    assert issue["evidence"]["canonical_level_count"] < issue["evidence"]["raw_level_count"]


def test_outliers_flagged_but_not_removed():
    df = pd.DataFrame({"v": [10, 11, 12, 13, 10, 12, 11, 13, 12, 11, 10, 12, 5000]})
    report = analyze_quality(_ds(df))
    issue = next(i for i in report["issues"] if i["code"] == "outliers::v")
    assert issue["evidence"]["iqr_outliers"] >= 1
    assert issue["suggested_operation"]["params"]["strategy"] == "flag"


def test_constant_column_detected():
    df = pd.DataFrame({"c": ["same"] * 10, "x": range(10)})
    report = analyze_quality(_ds(df))
    assert any(i["code"] == "constant::c" for i in report["issues"])


def test_potential_leakage_flagged_by_name():
    df = pd.DataFrame({"churn_probability": [0.1] * 10, "x": range(10)})
    report = analyze_quality(_ds(df))
    assert any(i["dimension"] == "potential_leakage" for i in report["issues"])


def test_quality_score_is_deterministic_and_bounded():
    df = pd.DataFrame({"a": [1, None, 3, 4, 5, 6, 7, 8, 9, 10], "b": range(10)})
    ds = _ds(df)
    r1 = analyze_quality(ds)["score"]
    r2 = analyze_quality(ds)["score"]
    assert r1 == r2
    assert 0 <= r1["overall"] <= 100
    assert {d["key"] for d in r1["dimensions"]} == {
        "missing_values", "duplicates", "data_types",
        "categorical_consistency", "outliers", "constant_columns", "potential_leakage",
    }


def test_clean_dataset_scores_higher_than_messy():
    clean = pd.DataFrame({"a": range(100), "b": [i * 2 for i in range(100)]})
    messy = clean.copy()
    messy.loc[:30, "a"] = None
    messy = pd.concat([messy, messy.head(20)], ignore_index=True)
    assert analyze_quality(_ds(clean))["score"]["overall"] > analyze_quality(_ds(messy))["score"]["overall"]
