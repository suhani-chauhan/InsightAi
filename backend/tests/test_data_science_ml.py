"""AutoML: task detection, leakage-safe training, comparison, prediction (master spec §22–§37)."""

import numpy as np
import pandas as pd
import pytest

from app.data_science.dataset import Dataset
from app.data_science.demo_data import DEMO_TARGET, build_demo_dataframe
from app.data_science import analyze_quality, recommend_cleaning
from app.data_science.cleaning import CleaningSession
from app.data_science.ml import detect_task, predict_with_bundle, train_and_compare


@pytest.fixture(scope="module")
def demo_clean() -> Dataset:
    df = build_demo_dataframe(n=500, seed=3)
    ds = Dataset.from_records(df.columns, df.to_dict("records"))
    recs = recommend_cleaning(ds, analyze_quality(ds))
    session = CleaningSession.start(ds.df)
    session.apply([r["operation"] for r in recs["recommendations"] if r["risk"] == "low"])
    return ds.with_df(session.current)


def _classification_df(n=300):
    rng = np.random.default_rng(1)
    x1 = rng.normal(0, 1, n)
    x2 = rng.normal(0, 1, n)
    y = ((x1 + x2 + rng.normal(0, 0.5, n)) > 0).astype(int)
    return pd.DataFrame({"x1": x1, "x2": x2, "cat": rng.choice(["a", "b", "c"], n), "target": y})


def _regression_df(n=300):
    rng = np.random.default_rng(2)
    x1 = rng.normal(0, 1, n)
    x2 = rng.normal(0, 1, n)
    y = 3 * x1 - 2 * x2 + rng.normal(0, 0.3, n)
    return pd.DataFrame({"x1": x1, "x2": x2, "target": y})


def test_detect_classification_for_categorical_target():
    ds = Dataset.from_records(*_dsargs(_classification_df()))
    detail = detect_task(ds, "target")
    assert detail["detected_task"] == "classification"
    assert "class_distribution" in detail


def test_detect_regression_for_continuous_target():
    ds = Dataset.from_records(*_dsargs(_regression_df()))
    detail = detect_task(ds, "target")
    assert detail["detected_task"] == "regression"
    assert detail["default_primary_metric"] == "r2"


def _dsargs(df):
    return df.columns, df.to_dict("records")


def test_classification_training_produces_real_metrics():
    ds = Dataset.from_records(*_dsargs(_classification_df()))
    bundle = train_and_compare(ds, "target", cross_validation=False)
    assert bundle.task == "classification"
    assert len(bundle.comparison) >= 3
    for row in bundle.comparison:
        if "error" in row:
            continue
        assert 0.0 <= row["accuracy"] <= 1.0
        assert 0.0 <= row["f1"] <= 1.0
        assert "confusion_matrix" in row
    # Signal is real -> a decent model should beat coin flip.
    assert bundle.metrics["accuracy"] > 0.7
    assert bundle.n_train > bundle.n_test


def test_regression_training_produces_real_metrics():
    ds = Dataset.from_records(*_dsargs(_regression_df()))
    bundle = train_and_compare(ds, "target", cross_validation=False)
    assert bundle.task == "regression"
    best = bundle.metrics
    assert best["r2"] > 0.8  # strong linear signal
    assert best["rmse"] >= 0
    assert "mae" in best and "mse" in best


def test_best_model_selected_by_primary_metric():
    ds = Dataset.from_records(*_dsargs(_classification_df()))
    bundle = train_and_compare(ds, "target", primary_metric="f1", cross_validation=False)
    scored = [r for r in bundle.comparison if "error" not in r]
    best_row = next(r for r in scored if r["is_best"])
    assert best_row["f1"] == max(r["f1"] for r in scored)


def test_train_test_split_prevents_leakage_via_pipeline():
    # The fitted estimator must be a Pipeline whose first step is the preprocessor
    # (imputers/scalers/encoders fitted on train folds only).
    ds = Dataset.from_records(*_dsargs(_classification_df()))
    bundle = train_and_compare(ds, "target", cross_validation=False)
    steps = dict(bundle.pipeline.named_steps)
    assert "prep" in steps and "model" in steps
    assert steps["prep"].__class__.__name__ == "ColumnTransformer"


def test_identifier_columns_auto_excluded():
    df = _classification_df()
    df.insert(0, "row_id", [f"id-{i}" for i in range(len(df))])
    ds = Dataset.from_records(df.columns, df.to_dict("records"))
    bundle = train_and_compare(ds, "target", cross_validation=False)
    assert "row_id" not in bundle.feature_columns
    assert any("row_id" in w for w in bundle.warnings)


def test_feature_importance_present_and_collapsed():
    ds = Dataset.from_records(*_dsargs(_classification_df()))
    bundle = train_and_compare(ds, "target", cross_validation=False)
    assert bundle.feature_importance
    feats = {f["feature"] for f in bundle.feature_importance}
    # one-hot columns collapsed back to "cat", not "cat_a"/"cat_b"
    assert "cat" in feats or all("cat_" not in f for f in feats)
    assert all("method" in f for f in bundle.feature_importance)


def test_prediction_uses_training_pipeline():
    ds = Dataset.from_records(*_dsargs(_classification_df()))
    bundle = train_and_compare(ds, "target", cross_validation=False)
    out = predict_with_bundle(bundle, {"x1": 2.0, "x2": 2.0, "cat": "a"})
    assert "prediction" in out
    assert "probabilities" in out and abs(sum(out["probabilities"].values()) - 1.0) < 1e-6


def test_example_row_is_a_real_complete_row():
    ds = Dataset.from_records(*_dsargs(_classification_df()))
    bundle = train_and_compare(ds, "target", cross_validation=False)
    assert set(bundle.example_row) <= set(bundle.feature_columns)
    assert bundle.example_row  # non-empty
    # every value is concrete (not NaN/None) so the default prediction is realistic
    assert all(v is not None for v in bundle.example_row.values())
    predicted = predict_with_bundle(bundle, bundle.example_row)
    assert "prediction" in predicted


def test_demo_dataset_full_pipeline(demo_clean):
    detail = detect_task(demo_clean, DEMO_TARGET)
    assert detail["detected_task"] == "classification"
    bundle = train_and_compare(demo_clean, DEMO_TARGET, cross_validation=False)
    assert bundle.best_model_name
    assert bundle.metrics[bundle.primary_metric] is not None
    assert bundle.feature_importance


def test_training_row_cap_enforced():
    big = pd.DataFrame({"x": np.arange(25_000), "target": np.arange(25_000) % 2})
    ds = Dataset.from_records(big.columns, big.to_dict("records"))
    # Dataset itself caps at 50k; force the ML cap by patching lower is overkill —
    # instead assert the guard message path with a frame above MAX_TRAIN_ROWS.
    from app.data_science import ml

    ds.df = ds.df  # 25k rows > MAX_TRAIN_ROWS (20k)
    with pytest.raises(ValueError, match="capped"):
        train_and_compare(ds, "target")
