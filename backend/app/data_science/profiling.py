"""Deterministic dataset + column profiling (master spec §7).

Nothing here is estimated or model-generated. Every figure is a pandas / numpy
computation over the analysis copy.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.data_science.dataset import ColumnKind, Dataset, _json_safe

_HIGH_CARDINALITY_RATIO = 0.5
_NEAR_CONSTANT_DOMINANCE = 0.98


def profile_dataset(dataset: Dataset) -> dict[str, Any]:
    df = dataset.df
    kinds = dataset.column_kinds()

    n_rows = len(df)
    dup_mask = df.duplicated(keep=False)
    dup_rows = int(dup_mask.sum())

    columns = [_profile_column(df[col], kinds[col], n_rows) for col in df.columns]

    constant_cols = [c["name"] for c in columns if c["is_constant"]]
    near_constant_cols = [c["name"] for c in columns if c["is_near_constant"] and not c["is_constant"]]
    high_card_cols = [c["name"] for c in columns if c["is_high_cardinality"]]

    total_cells = n_rows * max(df.shape[1], 1)
    missing_cells = int(df.isna().sum().sum())

    return {
        "dataset": {
            "n_rows": int(n_rows),
            "n_cols": int(df.shape[1]),
            "n_numeric": sum(1 for k in kinds.values() if k == ColumnKind.NUMERIC),
            "n_categorical": sum(1 for k in kinds.values() if k == ColumnKind.CATEGORICAL),
            "n_datetime": sum(1 for k in kinds.values() if k == ColumnKind.DATETIME),
            "n_boolean": sum(1 for k in kinds.values() if k == ColumnKind.BOOLEAN),
            "n_text": sum(1 for k in kinds.values() if k == ColumnKind.TEXT),
            "n_empty": sum(1 for k in kinds.values() if k == ColumnKind.EMPTY),
            "missing_cells": missing_cells,
            "missing_pct": _pct(missing_cells, total_cells),
            "duplicate_rows": dup_rows,
            "duplicate_pct": _pct(dup_rows, n_rows),
            "constant_columns": constant_cols,
            "near_constant_columns": near_constant_cols,
            "high_cardinality_columns": high_card_cols,
            "memory_bytes": int(df.memory_usage(deep=True).sum()),
        },
        "columns": columns,
    }


def _profile_column(s: pd.Series, kind: ColumnKind, n_rows: int) -> dict[str, Any]:
    non_null = s.dropna()
    missing = int(s.isna().sum())
    nunique = int(non_null.nunique())

    out: dict[str, Any] = {
        "name": str(s.name),
        "kind": kind.value,
        "dtype": str(s.dtype),
        "count": int(len(non_null)),
        "missing": missing,
        "missing_pct": _pct(missing, n_rows),
        "unique": nunique,
        "unique_pct": _pct(nunique, max(len(non_null), 1)),
        "is_constant": nunique <= 1 and missing < n_rows,
        "is_near_constant": False,
        "is_high_cardinality": False,
        "top_values": [],
        "mean": None,
        "median": None,
        "mode": None,
        "std": None,
        "min": None,
        "max": None,
        "q1": None,
        "q3": None,
        "iqr": None,
        "skew": None,
        "outlier_count": 0,
        "histogram": None,
    }

    if non_null.empty:
        return out

    # Dominance of the most frequent value -> near constant.
    counts = non_null.value_counts()
    dominance = float(counts.iloc[0] / len(non_null))
    out["is_near_constant"] = dominance >= _NEAR_CONSTANT_DOMINANCE and nunique > 1
    out["top_values"] = [
        {"value": _json_safe(v), "count": int(c), "pct": _pct(int(c), len(non_null))}
        for v, c in counts.head(10).items()
    ]

    if kind in (ColumnKind.CATEGORICAL, ColumnKind.TEXT, ColumnKind.BOOLEAN):
        out["is_high_cardinality"] = (
            kind != ColumnKind.BOOLEAN
            and nunique > max(50, _HIGH_CARDINALITY_RATIO * len(non_null))
        )
        out["mode"] = _json_safe(counts.index[0])

    if kind == ColumnKind.NUMERIC:
        numeric = pd.to_numeric(non_null, errors="coerce").dropna()
        if not numeric.empty:
            q1 = float(numeric.quantile(0.25))
            q3 = float(numeric.quantile(0.75))
            iqr = q3 - q1
            lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            out.update(
                mean=_finite(numeric.mean()),
                median=_finite(numeric.median()),
                mode=_finite(numeric.mode().iloc[0]) if not numeric.mode().empty else None,
                std=_finite(numeric.std()),
                min=_finite(numeric.min()),
                max=_finite(numeric.max()),
                q1=_finite(q1),
                q3=_finite(q3),
                iqr=_finite(iqr),
                skew=_finite(numeric.skew()) if len(numeric) > 2 else 0.0,
                outlier_count=int(((numeric < lower) | (numeric > upper)).sum()),
                quantiles={
                    "p01": _finite(numeric.quantile(0.01)),
                    "p05": _finite(numeric.quantile(0.05)),
                    "p25": _finite(q1),
                    "p50": _finite(numeric.median()),
                    "p75": _finite(q3),
                    "p95": _finite(numeric.quantile(0.95)),
                    "p99": _finite(numeric.quantile(0.99)),
                },
                histogram=_histogram(numeric),
            )

    if kind == ColumnKind.DATETIME:
        dt = pd.to_datetime(non_null, errors="coerce").dropna()
        if not dt.empty:
            out.update(
                min=dt.min().isoformat(),
                max=dt.max().isoformat(),
                mode=_json_safe(counts.index[0]),
            )

    return out


def _histogram(numeric: pd.Series, bins: int = 20) -> dict[str, list[float]] | None:
    if numeric.nunique() < 2:
        return None
    counts, edges = np.histogram(numeric.to_numpy(), bins=min(bins, max(numeric.nunique(), 2)))
    return {
        "counts": [int(c) for c in counts],
        "bin_edges": [_finite(e) for e in edges],
    }


def _pct(part: int, whole: int) -> float:
    if not whole:
        return 0.0
    return round(100.0 * part / whole, 2)


def _finite(value: Any) -> float | None:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if np.isnan(f) or np.isinf(f):
        return None
    return round(f, 6)


__all__ = ["profile_dataset"]
