"""Smart cleaning: recommendations, operations, session history (master spec §10–§18)."""

import numpy as np
import pandas as pd
import pytest

from app.data_science.dataset import Dataset
from app.data_science.cleaning import CleaningSession, apply_operations, recommend_cleaning


def _ds(df: pd.DataFrame) -> Dataset:
    return Dataset.from_records(df.columns, df.to_dict("records"))


@pytest.fixture
def dirty() -> pd.DataFrame:
    rng = np.random.default_rng(0)
    df = pd.DataFrame(
        {
            "age": list(rng.integers(20, 60, 40).astype(float)),
            "gender": (["Male", "male", "M", "Female", "female"] * 8),
            "amount": [f"{v:,}" for v in rng.integers(1000, 9000, 40)],
            "score": list(rng.normal(50, 5, 40)),
        }
    )
    df.loc[:3, "age"] = np.nan
    return pd.concat([df, df.head(4)], ignore_index=True)  # add duplicates


def test_recommendations_have_problem_solution_reason_impact(dirty):
    recs = recommend_cleaning(_ds(dirty))["recommendations"]
    assert recs
    for r in recs:
        assert r["problem"] and r["solution"] and r["reason"] and r["expected_impact"]
        assert r["risk"] in ("low", "medium", "high")
        assert r["operation"]["op"]


def test_median_imputation_chosen_for_skewed_numeric():
    df = pd.DataFrame({"x": [1, 1, 1, 2, 2, 3, 4, 5, 100, None, None]})
    recs = recommend_cleaning(_ds(df))["recommendations"]
    impute = next(r for r in recs if r["operation"]["op"] == "impute_missing")
    assert impute["operation"]["params"]["strategy"] == "median"


def test_mean_imputation_chosen_for_symmetric_numeric():
    df = pd.DataFrame({"x": [10, 11, 9, 12, 8, 10, 11, 9, None, 10, 10, 9, 11, 12, 8, 10]})
    recs = recommend_cleaning(_ds(df))["recommendations"]
    impute = next((r for r in recs if r["operation"]["op"] == "impute_missing"), None)
    assert impute is not None
    assert impute["operation"]["params"]["strategy"] == "mean"


def test_apply_impute_removes_missing():
    df = pd.DataFrame({"x": [1.0, 2.0, None, 4.0, 5.0, None, 7.0, 8.0]})
    out, records = apply_operations(df, [{"op": "impute_missing", "params": {"column": "x", "strategy": "median"}}])
    assert out["x"].isna().sum() == 0
    assert records[0]["missing_before"] == 2
    assert records[0]["missing_after"] == 0


def test_drop_duplicates_reports_before_after(dirty):
    out, records = apply_operations(dirty, [{"op": "drop_duplicates", "params": {"keep": "first"}}])
    rec = records[0]
    assert rec["rows_before"] - rec["rows_after"] == rec["rows_removed"] == 4


def test_standardize_categories_merges_only_case_spacing():
    df = pd.DataFrame({"g": ["Male", "male ", "MALE", "Female", "female"]})
    out, records = apply_operations(df, [{"op": "standardize_categories", "params": {"column": "g"}}])
    assert set(out["g"].unique()) == {"Male", "Female"}
    assert records[0]["cells_changed"] == 3


def test_to_numeric_conversion():
    df = pd.DataFrame({"amount": ["1,000", "2,500", "bad", "4,000"]})
    out, records = apply_operations(df, [{"op": "to_numeric", "params": {"column": "amount"}}])
    assert pd.api.types.is_numeric_dtype(out["amount"])
    assert out["amount"].tolist()[:2] == [1000.0, 2500.0]
    assert records[0]["failed_conversions"] == 1


def test_outlier_flag_adds_column_keeps_rows():
    df = pd.DataFrame({"v": [10, 11, 12, 13, 10, 12, 11, 13, 12, 11, 10, 12, 9000]})
    out, _ = apply_operations(df, [{"op": "handle_outliers", "params": {"column": "v", "strategy": "flag"}}])
    assert "v__is_outlier" in out.columns
    assert len(out) == len(df)
    assert bool(out["v__is_outlier"].iloc[-1]) is True


def test_outlier_cap_winsorizes():
    df = pd.DataFrame({"v": [10, 11, 12, 13, 10, 12, 11, 13, 12, 11, 10, 12, 9000]})
    out, _ = apply_operations(df, [{"op": "handle_outliers", "params": {"column": "v", "strategy": "cap"}}])
    assert out["v"].max() < 9000


def test_cleaning_session_history_undo_reset(dirty):
    session = CleaningSession.start(dirty)
    original_rows = len(session.current)
    session.apply([{"op": "drop_duplicates", "params": {"keep": "first"}}])
    assert len(session.history) == 1
    assert len(session.current) == original_rows - 4
    session.apply([{"op": "impute_missing", "params": {"column": "age", "strategy": "median"}}])
    assert len(session.history) == 2
    assert session.current["age"].isna().sum() == 0

    assert session.undo() is True
    assert len(session.history) == 1
    assert session.current["age"].isna().sum() > 0  # imputation undone
    assert len(session.current) == original_rows - 4  # dedupe still applied

    session.reset()
    assert len(session.history) == 0
    assert len(session.current) == original_rows


def test_preview_does_not_mutate_session(dirty):
    session = CleaningSession.start(dirty)
    before = session.current.copy()
    preview = session.preview([{"op": "drop_duplicates", "params": {"keep": "first"}}])
    assert preview["before"]["rows"] == len(before)
    assert preview["after"]["rows"] == len(before) - 4
    pd.testing.assert_frame_equal(session.current, before)  # untouched


def test_unknown_operation_raises():
    with pytest.raises(ValueError):
        apply_operations(pd.DataFrame({"a": [1]}), [{"op": "nuke_everything", "params": {}}])
