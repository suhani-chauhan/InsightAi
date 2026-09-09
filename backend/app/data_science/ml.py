"""AutoML: task detection, leakage-safe pipelines, model comparison, prediction.

Design guarantees (master spec §22–§37):
  * Models are really trained on the selected dataset — no synthetic metrics.
  * The train/test split happens **before** any imputer / scaler / encoder is
    fitted; all preprocessing lives inside an sklearn ``Pipeline`` +
    ``ColumnTransformer`` so the test fold never influences training.
  * Prediction reuses the exact fitted pipeline.
  * Feature importance is native for tree/linear models, permutation otherwise.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from app.data_science.dataset import ColumnKind, Dataset, classify_column, _json_safe

# Guardrails for synchronous training (master spec §52).
MAX_TRAIN_ROWS = 20_000
MAX_TRAIN_FEATURES = 60
MAX_HIGH_CARDINALITY = 40

RANDOM_STATE = 42


@dataclass
class TrainedModelBundle:
    """Everything needed to score and to serve predictions later."""

    task: str
    target: str
    primary_metric: str
    best_model_name: str
    pipeline: Any
    feature_columns: list[str]
    feature_schema: list[dict[str, Any]] = field(default_factory=list)
    example_row: dict[str, Any] = field(default_factory=dict)
    label_classes: list[Any] | None = None
    comparison: list[dict[str, Any]] = field(default_factory=list)
    feature_importance: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    n_train: int = 0
    n_test: int = 0
    warnings: list[str] = field(default_factory=list)


# ------------------------------------------------------------- task detection
def detect_task(dataset: Dataset, target: str) -> dict[str, Any]:
    if target not in dataset.df.columns:
        raise ValueError(f"Target column '{target}' is not in the dataset.")
    s = dataset.df[target].dropna()
    if s.empty:
        raise ValueError(f"Target column '{target}' is entirely missing.")

    kind = classify_column(s)
    nunique = int(s.nunique())
    n = int(len(s))

    if kind in (ColumnKind.CATEGORICAL, ColumnKind.BOOLEAN, ColumnKind.TEXT):
        task = "classification"
    elif kind == ColumnKind.NUMERIC:
        # Small number of distinct integers -> treat as classes.
        is_intish = np.allclose(pd.to_numeric(s, errors="coerce").dropna() % 1, 0)
        task = "classification" if (nunique <= 10 and is_intish and nunique / n < 0.05) else "regression"
    else:
        task = "classification"

    detail: dict[str, Any] = {
        "target": target,
        "detected_task": task,
        "target_kind": kind.value,
        "unique_values": nunique,
        "missing": int(dataset.df[target].isna().sum()),
    }
    if task == "classification":
        dist = s.value_counts()
        detail["class_distribution"] = {str(k): int(v) for k, v in dist.items()}
        detail["is_imbalanced"] = bool((dist.min() / dist.sum()) < 0.2) if len(dist) else False
        detail["default_primary_metric"] = "f1" if detail.get("is_imbalanced") else "accuracy"
    else:
        detail["default_primary_metric"] = "r2"
        detail["target_stats"] = {
            "mean": float(pd.to_numeric(s, errors="coerce").mean()),
            "std": float(pd.to_numeric(s, errors="coerce").std()),
            "min": float(pd.to_numeric(s, errors="coerce").min()),
            "max": float(pd.to_numeric(s, errors="coerce").max()),
        }
    return detail


# ------------------------------------------------------------------- features
def _prepare_features(
    dataset: Dataset, target: str, drop_columns: list[str] | None
) -> tuple[pd.DataFrame, pd.Series, list[str], list[str], list[str]]:
    df = dataset.df
    drop = set(drop_columns or [])
    kinds = dataset.column_kinds()

    # Auto-exclude obvious identifier columns (master spec §26).
    auto_dropped: list[str] = []
    for col in df.columns:
        if col == target or col in drop:
            continue
        name = str(col).lower()
        non_null = df[col].dropna()
        looks_id = (name == "id" or name.endswith("_id") or name.endswith("id")) and non_null.nunique() > 0.9 * max(len(non_null), 1)
        if looks_id:
            drop.add(col)
            auto_dropped.append(col)

    frame = df.drop(columns=[c for c in drop if c in df.columns], errors="ignore")
    frame = frame.dropna(subset=[target])
    y = frame[target]
    X = frame.drop(columns=[target])

    numeric_features: list[str] = []
    categorical_features: list[str] = []
    for col in list(X.columns):
        kind = kinds.get(col, classify_column(X[col]))
        if kind == ColumnKind.BOOLEAN:
            # True booleans / 0-1 numerics -> numeric; textual yes/no -> categorical.
            if pd.api.types.is_bool_dtype(X[col]):
                X[col] = X[col].astype("float64")
                numeric_features.append(col)
            elif pd.api.types.is_numeric_dtype(X[col]):
                numeric_features.append(col)
            else:
                categorical_features.append(col)
            continue
        if kind == ColumnKind.NUMERIC:
            numeric_features.append(col)
        elif kind == ColumnKind.DATETIME:
            # Expand into ordinal + parts, then treat as numeric.
            dt = pd.to_datetime(X[col], errors="coerce")
            X[f"{col}__year"] = dt.dt.year
            X[f"{col}__month"] = dt.dt.month
            X[f"{col}__dow"] = dt.dt.dayofweek
            numeric_features += [f"{col}__year", f"{col}__month", f"{col}__dow"]
            X = X.drop(columns=[col])
        elif kind == ColumnKind.TEXT:
            X = X.drop(columns=[col])  # free text not modelled in the baseline
        else:
            if X[col].nunique() <= MAX_HIGH_CARDINALITY:
                categorical_features.append(col)
            else:
                X = X.drop(columns=[col])

    # Normalise numeric columns to plain float64 so sklearn's imputer/scaler
    # never sees a pandas nullable dtype (Int64 / boolean).
    for col in numeric_features:
        X[col] = pd.to_numeric(X[col], errors="coerce").astype("float64")
    for col in categorical_features:
        X[col] = X[col].astype("object")

    return X, y, numeric_features, categorical_features, auto_dropped


def _build_preprocessor(numeric_features: list[str], categorical_features: list[str]) -> ColumnTransformer:
    numeric_pipe = Pipeline(
        [("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]
    )
    categorical_pipe = Pipeline(
        [
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", min_frequency=0.01)),
        ]
    )
    return ColumnTransformer(
        [
            ("num", numeric_pipe, numeric_features),
            ("cat", categorical_pipe, categorical_features),
        ],
        remainder="drop",
    )


def _model_zoo(task: str) -> dict[str, Any]:
    if task == "classification":
        from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
        from sklearn.linear_model import LogisticRegression
        from sklearn.neighbors import KNeighborsClassifier
        from sklearn.tree import DecisionTreeClassifier

        return {
            "Logistic Regression": LogisticRegression(max_iter=1000),
            "Decision Tree": DecisionTreeClassifier(random_state=RANDOM_STATE, max_depth=12),
            "Random Forest": RandomForestClassifier(n_estimators=200, random_state=RANDOM_STATE, n_jobs=-1),
            "K-Nearest Neighbors": KNeighborsClassifier(),
            "Gradient Boosting": GradientBoostingClassifier(random_state=RANDOM_STATE),
        }
    from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
    from sklearn.linear_model import Lasso, LinearRegression, Ridge
    from sklearn.tree import DecisionTreeRegressor

    return {
        "Linear Regression": LinearRegression(),
        "Ridge": Ridge(random_state=RANDOM_STATE),
        "Lasso": Lasso(random_state=RANDOM_STATE),
        "Decision Tree": DecisionTreeRegressor(random_state=RANDOM_STATE, max_depth=12),
        "Random Forest": RandomForestRegressor(n_estimators=200, random_state=RANDOM_STATE, n_jobs=-1),
        "Gradient Boosting": GradientBoostingRegressor(random_state=RANDOM_STATE),
    }


# -------------------------------------------------------------------- metrics
def _classification_metrics(y_true, y_pred, y_proba, classes) -> dict[str, Any]:
    from sklearn.metrics import (
        accuracy_score,
        confusion_matrix,
        f1_score,
        precision_score,
        recall_score,
        roc_auc_score,
    )

    binary = len(classes) == 2
    kw: dict[str, Any] = {"zero_division": 0}
    if binary:
        # pos_label must be an actual label; classes is sorted, take the last.
        kw.update(average="binary", pos_label=classes[-1])
    else:
        kw.update(average="macro")
    metrics = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, **kw)),
        "recall": float(recall_score(y_true, y_pred, **kw)),
        "f1": float(f1_score(y_true, y_pred, **kw)),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=classes).tolist(),
        "labels": [_json_safe(c) for c in classes],
    }
    try:
        if y_proba is not None:
            if binary:
                y_bin = (np.asarray(y_true) == classes[-1]).astype(int)
                metrics["roc_auc"] = float(roc_auc_score(y_bin, y_proba[:, 1]))
            else:
                metrics["roc_auc"] = float(roc_auc_score(y_true, y_proba, multi_class="ovr", average="macro"))
    except (ValueError, IndexError):
        metrics["roc_auc"] = None
    return metrics


def _regression_metrics(y_true, y_pred) -> dict[str, Any]:
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

    mse = float(mean_squared_error(y_true, y_pred))
    return {
        "r2": float(r2_score(y_true, y_pred)),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "mse": mse,
        "rmse": float(np.sqrt(mse)),
    }


_METRIC_LABELS = {
    "accuracy": "Accuracy",
    "precision": "Precision",
    "recall": "Recall",
    "f1": "F1 Score",
    "roc_auc": "ROC-AUC",
    "r2": "R²",
    "mae": "MAE",
    "mse": "MSE",
    "rmse": "RMSE",
}
_LOWER_IS_BETTER = {"mae", "mse", "rmse"}


# ---------------------------------------------------------------------- train
def train_and_compare(
    dataset: Dataset,
    target: str,
    *,
    task: str | None = None,
    models: list[str] | None = None,
    test_size: float = 0.2,
    primary_metric: str | None = None,
    cross_validation: bool = True,
    drop_columns: list[str] | None = None,
) -> TrainedModelBundle:
    detection = detect_task(dataset, target)
    task = task or detection["detected_task"]
    primary_metric = primary_metric or detection["default_primary_metric"]

    if len(dataset.df) > MAX_TRAIN_ROWS:
        raise ValueError(
            f"Dataset has {len(dataset.df):,} rows; synchronous training is capped at {MAX_TRAIN_ROWS:,}. "
            "Sample the data first."
        )

    X, y, numeric_features, categorical_features, auto_dropped = _prepare_features(dataset, target, drop_columns)
    warnings: list[str] = []
    if auto_dropped:
        warnings.append(f"Excluded likely identifier column(s): {', '.join(auto_dropped)}.")
    if not numeric_features and not categorical_features:
        raise ValueError("No usable feature columns remain after preprocessing.")
    if len(numeric_features) + len(categorical_features) > MAX_TRAIN_FEATURES:
        raise ValueError(
            f"{len(numeric_features) + len(categorical_features)} feature columns exceed the {MAX_TRAIN_FEATURES} cap for synchronous training."
        )

    label_classes: list[Any] | None = None
    stratify = None
    if task == "classification":
        y = y.astype("string")
        counts = y.value_counts()
        if (counts < 2).any():
            rare = counts[counts < 2].index.tolist()
            mask = ~y.isin(rare)
            X, y = X.loc[mask], y.loc[mask]
            warnings.append(f"Dropped {len(rare)} class(es) with a single sample.")
        if y.value_counts().min() >= 2:
            stratify = y
        label_classes = sorted(y.dropna().unique().tolist(), key=str)
    else:
        y = pd.to_numeric(y, errors="coerce").astype("float64")
        mask = y.notna()
        X, y = X.loc[mask], y.loc[mask]

    if len(X) < 20:
        raise ValueError(f"Only {len(X)} usable rows — need at least 20 to train and evaluate.")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=RANDOM_STATE, stratify=stratify
    )

    zoo = _model_zoo(task)
    chosen = {k: v for k, v in zoo.items() if not models or k in models} or zoo
    preprocessor = _build_preprocessor(numeric_features, categorical_features)

    comparison: list[dict[str, Any]] = []
    fitted: dict[str, Pipeline] = {}
    start = time.time()

    for name, estimator in chosen.items():
        pipe = Pipeline([("prep", preprocessor), ("model", estimator)])
        try:
            pipe.fit(X_train, y_train)
        except Exception as exc:  # noqa: BLE001 - report, don't crash the run
            comparison.append({"model": name, "error": str(exc)[:200]})
            continue
        y_pred = pipe.predict(X_test)
        if task == "classification":
            proba = pipe.predict_proba(X_test) if hasattr(pipe[-1], "predict_proba") else None
            row = _classification_metrics(y_test, y_pred, proba, label_classes)
        else:
            row = _regression_metrics(y_test, y_pred)

        if cross_validation and len(X_train) >= 50:
            try:
                scoring = _cv_scoring(task, primary_metric)
                cv_scores = cross_val_score(pipe, X_train, y_train, cv=min(5, y_train.value_counts().min() if task == "classification" else 5), scoring=scoring, n_jobs=-1)
                row["cv_mean"] = float(np.mean(cv_scores))
                row["cv_std"] = float(np.std(cv_scores))
            except Exception:  # noqa: BLE001
                pass

        row["model"] = name
        comparison.append(row)
        fitted[name] = pipe

        if time.time() - start > 90:
            warnings.append("Training time budget reached — remaining models were skipped.")
            break

    scored = [r for r in comparison if "error" not in r and primary_metric in r]
    if not scored:
        raise ValueError("Every candidate model failed to train on this dataset.")

    reverse = primary_metric not in _LOWER_IS_BETTER
    scored.sort(key=lambda r: r[primary_metric], reverse=reverse)
    best = scored[0]
    best_name = best["model"]
    best_pipe = fitted[best_name]

    importance = _feature_importance(best_pipe, X_test, y_test, task, numeric_features + categorical_features)
    feature_schema = _feature_schema(dataset, list(X.columns), numeric_features, categorical_features)
    example_row = _example_row(X_test, list(X.columns))

    return TrainedModelBundle(
        task=task,
        target=target,
        primary_metric=primary_metric,
        best_model_name=best_name,
        pipeline=best_pipe,
        feature_columns=list(X.columns),
        feature_schema=feature_schema,
        example_row=example_row,
        label_classes=[_json_safe(c) for c in label_classes] if label_classes else None,
        comparison=_decorate_comparison(comparison, primary_metric, best_name),
        feature_importance=importance,
        metrics=best,
        n_train=len(X_train),
        n_test=len(X_test),
        warnings=warnings,
    )


def _example_row(X_test: pd.DataFrame, feature_columns: list[str]) -> dict[str, Any]:
    """A real, mostly-complete test-set row to pre-fill the prediction form.

    Prefer a fully non-null row so the default prediction is a realistic point
    rather than a degenerate all-median one.
    """
    if X_test.empty:
        return {}
    complete = X_test.dropna()
    source = complete if not complete.empty else X_test
    row = source.iloc[len(source) // 2]
    return {col: _json_safe(row[col]) for col in feature_columns if col in row.index}


def _cv_scoring(task: str, primary_metric: str) -> str:
    if task == "regression":
        return {"r2": "r2", "mae": "neg_mean_absolute_error", "mse": "neg_mean_squared_error", "rmse": "neg_root_mean_squared_error"}.get(primary_metric, "r2")
    return {"accuracy": "accuracy", "f1": "f1_weighted", "precision": "precision_weighted", "recall": "recall_weighted", "roc_auc": "roc_auc_ovr_weighted"}.get(primary_metric, "accuracy")


def _decorate_comparison(comparison: list[dict[str, Any]], primary_metric: str, best_name: str) -> list[dict[str, Any]]:
    out = []
    for row in comparison:
        row = dict(row)
        row["is_best"] = row.get("model") == best_name
        row["primary_metric"] = primary_metric
        row["primary_score"] = row.get(primary_metric)
        out.append(row)
    return out


# --------------------------------------------------------- feature importance
def _feature_importance(
    pipe: Pipeline, X_test: pd.DataFrame, y_test, task: str, source_features: list[str] | None = None
) -> list[dict[str, Any]]:
    model = pipe[-1]
    prep = pipe[:-1]
    try:
        feature_names = list(prep.get_feature_names_out())
    except Exception:  # noqa: BLE001
        feature_names = None

    raw: np.ndarray | None = None
    method = "native"
    if hasattr(model, "feature_importances_"):
        raw = np.asarray(model.feature_importances_, dtype=float)
    elif hasattr(model, "coef_"):
        coef = np.asarray(model.coef_, dtype=float)
        raw = np.abs(coef).mean(axis=0) if coef.ndim > 1 else np.abs(coef)
    else:
        method = "permutation"
        try:
            result = permutation_importance(pipe, X_test, y_test, n_repeats=5, random_state=RANDOM_STATE, n_jobs=-1)
            raw = result.importances_mean
            feature_names = list(X_test.columns)
        except Exception:  # noqa: BLE001
            return []

    if raw is None or feature_names is None or len(raw) != len(feature_names):
        return []

    total = float(np.sum(np.abs(raw))) or 1.0
    sources = sorted(source_features or [], key=len, reverse=True)

    def _to_source(name: str) -> str:
        cleaned = _clean_feature_name(name)
        for src in sources:
            if cleaned == src or cleaned.startswith(f"{src}_"):
                return src
        return cleaned.split("=")[0]

    # Collapse one-hot columns back to their source feature.
    collapsed: dict[str, dict[str, Any]] = {}
    for n, v in zip(feature_names, raw):
        base = _to_source(n)
        entry = collapsed.setdefault(base, {"feature": base, "importance": 0.0, "raw": 0.0})
        entry["importance"] += float(v) / total
        entry["raw"] += float(v)
    ranked = sorted(collapsed.values(), key=lambda d: abs(d["importance"]), reverse=True)
    for r in ranked:
        r["importance"] = round(r["importance"], 4)
        r["raw"] = round(r["raw"], 6)
    return [{"method": method, **r} for r in ranked[:20]]


def _clean_feature_name(name: str) -> str:
    for prefix in ("num__", "cat__", "remainder__"):
        if name.startswith(prefix):
            name = name[len(prefix):]
    return name.replace("__year", " (year)").replace("__month", " (month)").replace("__dow", " (day of week)")


def _feature_schema(dataset: Dataset, feature_columns: list[str], numeric_features: list[str], categorical_features: list[str]) -> list[dict[str, Any]]:
    schema: list[dict[str, Any]] = []
    df = dataset.df
    for col in feature_columns:
        if col in numeric_features:
            base = col.split("__")[0]
            series = pd.to_numeric(df[base], errors="coerce") if base in df.columns else pd.Series(dtype=float)
            schema.append(
                {
                    "name": col,
                    "type": "number",
                    "min": _json_safe(series.min()) if not series.empty else None,
                    "max": _json_safe(series.max()) if not series.empty else None,
                    "median": _json_safe(series.median()) if not series.empty else None,
                }
            )
        elif col in categorical_features:
            options = [_json_safe(v) for v in df[col].dropna().value_counts().head(50).index.tolist()]
            schema.append({"name": col, "type": "category", "options": options})
    return schema


# ------------------------------------------------------------------- predict
def predict_with_bundle(bundle: TrainedModelBundle, feature_values: dict[str, Any]) -> dict[str, Any]:
    row = {}
    for col in bundle.feature_columns:
        row[col] = feature_values.get(col, np.nan)
    frame = pd.DataFrame([row], columns=bundle.feature_columns)
    for entry in bundle.feature_schema:
        if entry["type"] == "number":
            frame[entry["name"]] = pd.to_numeric(frame[entry["name"]], errors="coerce")

    pred = bundle.pipeline.predict(frame)[0]
    out: dict[str, Any] = {"prediction": _json_safe(pred)}
    model = bundle.pipeline[-1]
    if bundle.task == "classification" and hasattr(model, "predict_proba"):
        proba = bundle.pipeline.predict_proba(frame)[0]
        classes = list(bundle.pipeline[-1].classes_)
        out["probabilities"] = {str(_json_safe(c)): round(float(p), 4) for c, p in zip(classes, proba)}
        out["confidence"] = round(float(np.max(proba)), 4)
    return out


__all__ = [
    "TrainedModelBundle",
    "detect_task",
    "train_and_compare",
    "predict_with_bundle",
    "MAX_TRAIN_ROWS",
    "MAX_TRAIN_FEATURES",
]
