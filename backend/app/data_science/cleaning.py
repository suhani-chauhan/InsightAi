"""Smart cleaning: recommendation engine, operation registry, session history.

Guarantees (master spec §10–§18):
  * Nothing is applied without the caller asking for it — the recommendation
    engine only *suggests*.
  * Every operation runs on the in-memory analysis copy; the source database is
    never touched here.
  * Each applied operation returns a structured record (before / after counts,
    strategy, affected column) for the cleaning history and the preview table.
  * Undo / reset are exact — the session keeps a snapshot per applied step.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np
import pandas as pd

from app.data_science.dataset import ColumnKind, Dataset, classify_column
from app.data_science.quality import analyze_quality

CleanOp = Callable[[pd.DataFrame, dict[str, Any]], "OpResult"]


@dataclass
class OpResult:
    df: pd.DataFrame
    record: dict[str, Any]


# --------------------------------------------------------------------- helpers
def _canonical(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value).strip())


def _skew_of(s: pd.Series) -> float:
    numeric = pd.to_numeric(s, errors="coerce").dropna()
    if len(numeric) < 3:
        return 0.0
    return float(numeric.skew())


# ---------------------------------------------------------------- operations
def op_trim_whitespace(df: pd.DataFrame, params: dict[str, Any]) -> OpResult:
    col = params["column"]
    before = df[col].astype("string")
    trimmed = before.str.replace(r"\s+", " ", regex=True).str.strip()
    changed = int((before.fillna("\x00") != trimmed.fillna("\x00")).sum())
    out = df.copy()
    out[col] = trimmed
    return OpResult(out, {"op": "trim_whitespace", "column": col, "cells_changed": changed, "action": "Trimmed whitespace"})


def op_standardize_categories(df: pd.DataFrame, params: dict[str, Any]) -> OpResult:
    col = params["column"]
    s = df[col].astype("string")
    non_null = s.dropna()
    groups: dict[str, list[str]] = {}
    for level in non_null.unique().tolist():
        groups.setdefault(_canonical(level).lower(), []).append(level)
    mapping: dict[str, str] = {}
    for members in groups.values():
        # Canonical label = most frequent original spelling in the group.
        counts = non_null[non_null.isin(members)].value_counts()
        canonical = counts.index[0]
        for m in members:
            if m != canonical:
                mapping[m] = canonical
    out = df.copy()
    out[col] = s.map(lambda v: mapping.get(v, v) if pd.notna(v) else v).astype("string")
    changed = int(s.isin(mapping.keys()).sum())
    return OpResult(
        out,
        {
            "op": "standardize_categories",
            "column": col,
            "cells_changed": changed,
            "mapping": mapping,
            "action": f"Standardised {len(mapping)} label variant(s)",
        },
    )


def op_to_numeric(df: pd.DataFrame, params: dict[str, Any]) -> OpResult:
    col = params["column"]
    cleaned = df[col].astype("string").str.replace(",", "", regex=False).str.strip()
    converted = pd.to_numeric(cleaned, errors="coerce")
    failed = int(converted.isna().sum() - df[col].isna().sum())
    out = df.copy()
    out[col] = converted
    return OpResult(
        out,
        {"op": "to_numeric", "column": col, "failed_conversions": max(failed, 0), "action": "Converted to numeric"},
    )


def op_to_datetime(df: pd.DataFrame, params: dict[str, Any]) -> OpResult:
    col = params["column"]
    converted = pd.to_datetime(df[col], errors="coerce")
    failed = int(converted.isna().sum() - df[col].isna().sum())
    out = df.copy()
    out[col] = converted
    return OpResult(
        out,
        {"op": "to_datetime", "column": col, "failed_conversions": max(failed, 0), "action": "Parsed as datetime"},
    )


def op_drop_duplicates(df: pd.DataFrame, params: dict[str, Any]) -> OpResult:
    keep = params.get("keep", "first")
    subset = params.get("subset") or None
    before = len(df)
    out = df.drop_duplicates(subset=subset, keep=keep).reset_index(drop=True)
    removed = before - len(out)
    return OpResult(
        out,
        {"op": "drop_duplicates", "rows_removed": removed, "rows_before": before, "rows_after": len(out), "action": f"Removed {removed} duplicate row(s)"},
    )


def op_drop_column(df: pd.DataFrame, params: dict[str, Any]) -> OpResult:
    col = params["column"]
    out = df.drop(columns=[col])
    return OpResult(out, {"op": "drop_column", "column": col, "action": f"Dropped column '{col}'"})


def op_drop_rows_missing(df: pd.DataFrame, params: dict[str, Any]) -> OpResult:
    cols = params.get("columns") or list(df.columns)
    before = len(df)
    out = df.dropna(subset=cols).reset_index(drop=True)
    removed = before - len(out)
    return OpResult(
        out,
        {"op": "drop_rows_missing", "columns": cols, "rows_removed": removed, "rows_before": before, "rows_after": len(out), "action": f"Dropped {removed} row(s) with missing values"},
    )


_NUMERIC_STRATEGIES = {"mean", "median", "mode", "constant", "knn"}


def op_impute_missing(df: pd.DataFrame, params: dict[str, Any]) -> OpResult:
    col = params["column"]
    strategy = params.get("strategy", "auto")
    s = df[col]
    missing_before = int(s.isna().sum())
    kind = classify_column(s)
    out = df.copy()

    if strategy == "auto":
        strategy = _auto_strategy(s, kind)

    fill_value: Any = params.get("value")
    if kind == ColumnKind.NUMERIC or pd.api.types.is_numeric_dtype(s):
        numeric = pd.to_numeric(s, errors="coerce")
        if strategy == "mean":
            fill_value = float(numeric.mean())
        elif strategy == "median":
            fill_value = float(numeric.median())
        elif strategy == "mode":
            fill_value = float(numeric.mode().iloc[0]) if not numeric.mode().empty else 0.0
        elif strategy == "constant":
            fill_value = float(params.get("value", 0))
        elif strategy == "knn":
            return _knn_impute(df, col)
        out[col] = numeric.fillna(fill_value)
    else:
        if strategy == "constant":
            fill_value = params.get("value", "Unknown")
        elif strategy in ("mode", "auto"):
            modes = s.dropna().mode()
            fill_value = modes.iloc[0] if not modes.empty else "Unknown"
        else:
            fill_value = params.get("value", "Unknown")
        out[col] = s.fillna(fill_value)

    return OpResult(
        out,
        {
            "op": "impute_missing",
            "column": col,
            "strategy": strategy,
            "fill_value": _plain(fill_value),
            "missing_before": missing_before,
            "missing_after": int(out[col].isna().sum()),
            "action": f"Imputed {missing_before} missing value(s) via {strategy}",
        },
    )


def _knn_impute(df: pd.DataFrame, col: str) -> OpResult:
    from sklearn.impute import KNNImputer

    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(pd.to_numeric(df[c], errors="coerce"))]
    numeric_cols = [c for c in numeric_cols if pd.to_numeric(df[c], errors="coerce").notna().mean() > 0.5]
    if col not in numeric_cols:
        numeric_cols.append(col)
    frame = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
    missing_before = int(frame[col].isna().sum())
    imputer = KNNImputer(n_neighbors=min(5, max(2, len(frame) // 20)))
    filled = pd.DataFrame(imputer.fit_transform(frame), columns=numeric_cols, index=frame.index)
    out = df.copy()
    out[col] = filled[col]
    return OpResult(
        out,
        {
            "op": "impute_missing",
            "column": col,
            "strategy": "knn",
            "missing_before": missing_before,
            "missing_after": int(out[col].isna().sum()),
            "action": f"Imputed {missing_before} missing value(s) via KNN (k={imputer.n_neighbors})",
        },
    )


def _auto_strategy(s: pd.Series, kind: ColumnKind) -> str:
    if kind == ColumnKind.NUMERIC or pd.api.types.is_numeric_dtype(s):
        return "median" if abs(_skew_of(s)) > 1.0 else "mean"
    return "mode"


def op_handle_outliers(df: pd.DataFrame, params: dict[str, Any]) -> OpResult:
    col = params["column"]
    strategy = params.get("strategy", "flag")  # keep | remove | cap | flag
    numeric = pd.to_numeric(df[col], errors="coerce")
    q1, q3 = numeric.quantile(0.25), numeric.quantile(0.75)
    iqr = q3 - q1
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    mask = (numeric < lower) | (numeric > upper)
    n_out = int(mask.sum())
    out = df.copy()

    if strategy == "remove":
        out = df.loc[~mask.fillna(False)].reset_index(drop=True)
        action = f"Removed {n_out} outlier row(s) from '{col}'"
    elif strategy == "cap":
        out[col] = numeric.clip(lower=lower, upper=upper)
        action = f"Capped {n_out} outlier(s) in '{col}' to the 1.5×IQR fences"
    elif strategy == "flag":
        out[f"{col}__is_outlier"] = mask.fillna(False)
        action = f"Flagged {n_out} outlier(s) in a new '{col}__is_outlier' column"
    else:
        action = f"Kept {n_out} outlier(s) in '{col}' (no change)"

    return OpResult(
        out,
        {
            "op": "handle_outliers",
            "column": col,
            "strategy": strategy,
            "outliers": n_out,
            "rows_before": len(df),
            "rows_after": len(out),
            "action": action,
        },
    )


def op_group_rare_categories(df: pd.DataFrame, params: dict[str, Any]) -> OpResult:
    col = params["column"]
    threshold = float(params.get("min_frequency", 0.01))
    label = params.get("label", "Other")
    freq = df[col].value_counts(normalize=True)
    rare = set(freq[freq < threshold].index)
    out = df.copy()
    out[col] = df[col].map(lambda v: label if v in rare else v)
    return OpResult(
        out,
        {"op": "group_rare_categories", "column": col, "levels_grouped": len(rare), "label": label, "action": f"Grouped {len(rare)} rare level(s) into '{label}'"},
    )


def op_map_categories(df: pd.DataFrame, params: dict[str, Any]) -> OpResult:
    col = params["column"]
    mapping = params["mapping"]
    out = df.copy()
    changed = int(df[col].isin(mapping.keys()).sum())
    out[col] = df[col].map(lambda v: mapping.get(v, v))
    return OpResult(out, {"op": "map_categories", "column": col, "cells_changed": changed, "action": f"Applied a {len(mapping)}-entry category mapping"})


CLEANING_OPERATIONS: dict[str, CleanOp] = {
    "trim_whitespace": op_trim_whitespace,
    "standardize_categories": op_standardize_categories,
    "to_numeric": op_to_numeric,
    "to_datetime": op_to_datetime,
    "drop_duplicates": op_drop_duplicates,
    "drop_column": op_drop_column,
    "drop_rows_missing": op_drop_rows_missing,
    "impute_missing": op_impute_missing,
    "handle_outliers": op_handle_outliers,
    "group_rare_categories": op_group_rare_categories,
    "map_categories": op_map_categories,
}

# Operations Smart Clean may apply without confirmation (master spec §15 Mode B).
LOW_RISK_OPERATIONS = {"trim_whitespace", "standardize_categories", "to_numeric", "drop_duplicates"}


def apply_operations(df: pd.DataFrame, operations: list[dict[str, Any]]) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    current = df
    records: list[dict[str, Any]] = []
    for spec in operations:
        op_name = spec.get("op")
        fn = CLEANING_OPERATIONS.get(op_name)
        if fn is None:
            raise ValueError(f"Unknown cleaning operation: {op_name!r}")
        params = spec.get("params", {})
        if "column" in params and params["column"] not in current.columns and op_name != "drop_column":
            records.append({"op": op_name, "skipped": True, "reason": f"column '{params['column']}' not present"})
            continue
        result = fn(current, params)
        current = result.df
        records.append(result.record)
    return current.reset_index(drop=True), records


# --------------------------------------------------------- recommendation eng.
def recommend_cleaning(dataset: Dataset, quality_report: dict[str, Any] | None = None) -> dict[str, Any]:
    """Turn quality issues into concrete, explained cleaning recommendations."""
    report = quality_report or analyze_quality(dataset)
    df = dataset.df
    recs: list[dict[str, Any]] = []

    for issue in report["issues"]:
        op = issue.get("suggested_operation")
        if not op:
            continue
        col = (issue["columns"] or [None])[0]
        rec = _build_recommendation(df, issue, op, col)
        if rec:
            recs.append(rec)

    safe = [r for r in recs if r["risk"] == "low"]
    return {
        "recommendations": recs,
        "safe_fix_count": len(safe),
        "review_count": len(recs) - len(safe),
    }


def _build_recommendation(df: pd.DataFrame, issue: dict[str, Any], op: dict[str, Any], col: str | None) -> dict[str, Any] | None:
    op_name = op["op"]
    params = dict(op.get("params", {}))
    n_rows = len(df)

    if op_name == "impute_missing" and col is not None:
        s = df[col]
        kind = classify_column(s)
        strategy = _auto_strategy(s, kind)
        params["strategy"] = strategy
        miss = int(s.isna().sum())
        if kind == ColumnKind.NUMERIC:
            skew = _skew_of(s)
            reason = (
                f"'{col}' is numeric and {'skewed' if abs(skew) > 1 else 'roughly symmetric'} "
                f"(skew={skew:.2f}); {strategy} imputation is {'robust to extreme values' if strategy == 'median' else 'appropriate for a symmetric distribution'}."
            )
        else:
            reason = f"'{col}' is categorical; filling the {miss} gap(s) with the most frequent value keeps the distribution stable."
        return {
            "id": issue["code"],
            "issue": issue["title"],
            "problem": issue["recommendation"].split(" — ")[0] if " — " in issue["recommendation"] else f"{col} has {miss} missing value(s)",
            "operation": {"op": op_name, "params": params},
            "solution": f"{strategy.title()} imputation" if kind == ColumnKind.NUMERIC else "Most-frequent (mode) imputation",
            "reason": reason,
            "expected_impact": f"Fills {miss} value(s); preserves all {n_rows} rows.",
            "risk": "low" if issue["severity"] in ("low", "info") else "medium",
        }

    if op_name == "drop_column" and col is not None:
        miss_pct = issue["evidence"].get("missing_pct", 100)
        return {
            "id": issue["code"],
            "issue": issue["title"],
            "problem": f"'{col}' — {issue['title'].lower()}",
            "operation": {"op": op_name, "params": params},
            "solution": f"Drop column '{col}'",
            "reason": (
                f"'{col}' is {'empty' if miss_pct >= 100 else f'{miss_pct:.0f}% missing' } or constant, so it "
                "cannot contribute reliable signal."
            ),
            "expected_impact": f"Removes 1 column; all {n_rows} rows kept.",
            "risk": "medium",
        }

    if op_name == "drop_duplicates":
        removed = issue["evidence"].get("duplicate_rows", 0)
        return {
            "id": issue["code"],
            "issue": issue["title"],
            "problem": f"{removed} exact duplicate row(s)",
            "operation": {"op": op_name, "params": {"keep": "first"}},
            "solution": "Remove duplicate rows, keep first occurrence",
            "reason": "Fully duplicated rows inflate counts and bias every downstream statistic and model.",
            "expected_impact": f"{n_rows} → {n_rows - removed} rows.",
            "risk": "low",
        }

    if op_name in ("standardize_categories", "trim_whitespace") and col is not None:
        return {
            "id": issue["code"],
            "issue": issue["title"],
            "problem": issue["recommendation"],
            "operation": {"op": op_name, "params": params},
            "solution": "Standardise category labels" if op_name == "standardize_categories" else "Trim whitespace",
            "reason": "Label variants that mean the same thing split counts and weaken grouping, encoding, and charts.",
            "expected_impact": f"Normalises labels in '{col}'; row count unchanged.",
            "risk": "low",
        }

    if op_name in ("to_numeric", "to_datetime") and col is not None:
        return {
            "id": issue["code"],
            "issue": issue["title"],
            "problem": issue["recommendation"],
            "operation": {"op": op_name, "params": params},
            "solution": f"Convert '{col}' to {'a number' if op_name == 'to_numeric' else 'a datetime'}",
            "reason": "Stored as text, this column can't be aggregated, scaled, or used numerically by a model.",
            "expected_impact": "Type change only; values that don't parse become missing and can then be imputed.",
            "risk": "low",
        }

    if op_name == "handle_outliers" and col is not None:
        n_out = issue["evidence"].get("iqr_outliers", 0)
        return {
            "id": issue["code"],
            "issue": issue["title"],
            "problem": f"{n_out} outlier(s) in '{col}'",
            "operation": {"op": op_name, "params": {"column": col, "strategy": "flag"}},
            "solution": "Flag outliers (do not remove)",
            "reason": "Outliers are often genuine events. Flagging keeps the data while letting you model or filter them explicitly.",
            "expected_impact": f"Adds a boolean '{col}__is_outlier' column; no rows or values removed.",
            "risk": "low",
        }

    return None


# --------------------------------------------------------------- session state
@dataclass
class CleaningStep:
    index: int
    operations: list[dict[str, Any]]
    records: list[dict[str, Any]]
    rows_before: int
    rows_after: int
    cols_before: int
    cols_after: int


@dataclass
class CleaningSession:
    """Owns the working DataFrame plus an exact-snapshot undo history."""

    original: pd.DataFrame
    current: pd.DataFrame
    history: list[CleaningStep] = field(default_factory=list)
    _snapshots: list[pd.DataFrame] = field(default_factory=list)

    @classmethod
    def start(cls, df: pd.DataFrame) -> "CleaningSession":
        base = df.copy(deep=True)
        return cls(original=base.copy(deep=True), current=base, _snapshots=[base.copy(deep=True)])

    def preview(self, operations: list[dict[str, Any]]) -> dict[str, Any]:
        new_df, records = apply_operations(self.current, operations)
        return {
            "before": _frame_stats(self.current),
            "after": _frame_stats(new_df),
            "column_diff": _column_diff(self.current, new_df, records),
            "operation_records": records,
        }

    def apply(self, operations: list[dict[str, Any]]) -> dict[str, Any]:
        new_df, records = apply_operations(self.current, operations)
        step = CleaningStep(
            index=len(self.history),
            operations=operations,
            records=records,
            rows_before=len(self.current),
            rows_after=len(new_df),
            cols_before=self.current.shape[1],
            cols_after=new_df.shape[1],
        )
        self.history.append(step)
        self._snapshots.append(new_df.copy(deep=True))
        self.current = new_df
        return {"step": step.__dict__, "current": _frame_stats(new_df)}

    def undo(self) -> bool:
        if not self.history:
            return False
        self.history.pop()
        self._snapshots.pop()
        self.current = self._snapshots[-1].copy(deep=True)
        return True

    def reset(self) -> None:
        self.current = self.original.copy(deep=True)
        self.history.clear()
        self._snapshots = [self.original.copy(deep=True)]

    def summary(self) -> dict[str, Any]:
        return {
            "steps": [s.__dict__ for s in self.history],
            "original": _frame_stats(self.original),
            "current": _frame_stats(self.current),
            "total_operations": sum(len(s.operations) for s in self.history),
        }


def _frame_stats(df: pd.DataFrame) -> dict[str, Any]:
    return {
        "rows": int(len(df)),
        "columns": int(df.shape[1]),
        "missing_cells": int(df.isna().sum().sum()),
        "duplicate_rows": int(df.duplicated(keep=False).sum()),
    }


def _column_diff(before: pd.DataFrame, after: pd.DataFrame, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    action_by_col: dict[str, str] = {}
    for rec in records:
        if rec.get("column"):
            action_by_col[rec["column"]] = rec.get("action", rec.get("op", ""))

    cols = list(dict.fromkeys(list(before.columns) + list(after.columns)))
    rows: list[dict[str, Any]] = []
    for col in cols:
        b_missing = int(before[col].isna().sum()) if col in before.columns else None
        a_missing = int(after[col].isna().sum()) if col in after.columns else None
        status = "unchanged"
        if col not in after.columns:
            status = "dropped"
        elif col not in before.columns:
            status = "added"
        elif b_missing != a_missing or str(before[col].dtype) != str(after[col].dtype):
            status = "modified"
        rows.append(
            {
                "column": col,
                "status": status,
                "missing_before": b_missing,
                "missing_after": a_missing,
                "dtype_before": str(before[col].dtype) if col in before.columns else None,
                "dtype_after": str(after[col].dtype) if col in after.columns else None,
                "action": action_by_col.get(col, ""),
            }
        )
    return rows


def _plain(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return round(float(value), 6)
    return value


__all__ = [
    "CleaningSession",
    "CleaningStep",
    "recommend_cleaning",
    "apply_operations",
    "CLEANING_OPERATIONS",
    "LOW_RISK_OPERATIONS",
    "OpResult",
]
