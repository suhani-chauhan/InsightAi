"""Exploratory Data Analysis (master spec §19–§20).

Produces:
  * numeric + categorical summaries (deterministic),
  * a correlation matrix (numeric columns),
  * chart specifications the frontend renders with its existing Recharts stack,
  * auto-insights whose every number is lifted from the computations above.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.data_science.dataset import ColumnKind, Dataset, _json_safe
from app.data_science.profiling import _finite, _histogram

_MAX_CHART_COLUMNS = 12
_MAX_BARS = 12


def run_eda(dataset: Dataset, target: str | None = None) -> dict[str, Any]:
    df = dataset.df
    kinds = dataset.column_kinds()
    numeric_cols = [c for c, k in kinds.items() if k == ColumnKind.NUMERIC]
    categorical_cols = [c for c, k in kinds.items() if k in (ColumnKind.CATEGORICAL, ColumnKind.BOOLEAN)]
    datetime_cols = [c for c, k in kinds.items() if k == ColumnKind.DATETIME]

    numeric_summary = [_numeric_summary(df[c]) for c in numeric_cols]
    categorical_summary = [_categorical_summary(df[c]) for c in categorical_cols]
    correlations = _correlations(df[numeric_cols]) if len(numeric_cols) >= 2 else None
    charts = _chart_specs(df, kinds, numeric_cols, categorical_cols, datetime_cols, target)
    insights = _auto_insights(df, kinds, numeric_summary, categorical_summary, correlations, target)

    return {
        "target": target,
        "numeric_summary": numeric_summary,
        "categorical_summary": categorical_summary,
        "correlations": correlations,
        "charts": charts,
        "insights": insights,
    }


def _numeric_summary(s: pd.Series) -> dict[str, Any]:
    numeric = pd.to_numeric(s, errors="coerce").dropna()
    if numeric.empty:
        return {"column": str(s.name), "count": 0}
    q1, q3 = numeric.quantile(0.25), numeric.quantile(0.75)
    return {
        "column": str(s.name),
        "count": int(len(numeric)),
        "mean": _finite(numeric.mean()),
        "median": _finite(numeric.median()),
        "std": _finite(numeric.std()),
        "min": _finite(numeric.min()),
        "max": _finite(numeric.max()),
        "q1": _finite(q1),
        "q3": _finite(q3),
        "iqr": _finite(q3 - q1),
        "skew": _finite(numeric.skew()) if len(numeric) > 2 else 0.0,
        "kurtosis": _finite(numeric.kurtosis()) if len(numeric) > 3 else 0.0,
    }


def _categorical_summary(s: pd.Series) -> dict[str, Any]:
    non_null = s.dropna()
    counts = non_null.value_counts()
    total = len(non_null)
    return {
        "column": str(s.name),
        "count": int(total),
        "unique": int(non_null.nunique()),
        "top": [
            {"value": _json_safe(v), "count": int(c), "pct": round(100 * c / total, 2) if total else 0.0}
            for v, c in counts.head(_MAX_BARS).items()
        ],
    }


def _correlations(numeric_df: pd.DataFrame) -> dict[str, Any]:
    frame = numeric_df.apply(pd.to_numeric, errors="coerce")
    corr = frame.corr(numeric_only=True).round(4)
    corr = corr.replace({np.nan: None})
    cols = list(corr.columns)
    pairs = []
    for i, a in enumerate(cols):
        for b in cols[i + 1 :]:
            val = corr.loc[a, b]
            if val is None:
                continue
            pairs.append({"a": a, "b": b, "corr": float(val)})
    pairs.sort(key=lambda p: abs(p["corr"]), reverse=True)
    return {
        "columns": cols,
        "matrix": [[None if corr.loc[r, c] is None else float(corr.loc[r, c]) for c in cols] for r in cols],
        "top_pairs": pairs[:10],
    }


def _chart_specs(
    df: pd.DataFrame,
    kinds: dict[str, ColumnKind],
    numeric_cols: list[str],
    categorical_cols: list[str],
    datetime_cols: list[str],
    target: str | None,
) -> list[dict[str, Any]]:
    charts: list[dict[str, Any]] = []

    for col in numeric_cols[:_MAX_CHART_COLUMNS]:
        numeric = pd.to_numeric(df[col], errors="coerce").dropna()
        hist = _histogram(numeric)
        if not hist:
            continue
        bins = []
        edges = hist["bin_edges"]
        for i, count in enumerate(hist["counts"]):
            bins.append({"bin": f"{edges[i]:.2f}", "range": [edges[i], edges[i + 1]], "count": count})
        charts.append({"kind": "histogram", "title": f"Distribution of {col}", "column": col, "data": bins})
        charts.append(
            {
                "kind": "box",
                "title": f"{col} — spread & outliers",
                "column": col,
                "data": _box_stats(numeric),
            }
        )

    for col in categorical_cols[:_MAX_CHART_COLUMNS]:
        summary = _categorical_summary(df[col])
        if summary["unique"] <= 1:
            continue
        charts.append(
            {
                "kind": "bar",
                "title": f"{col} — frequency",
                "column": col,
                "data": [{"label": str(t["value"]), "count": t["count"]} for t in summary["top"]],
            }
        )
        if summary["unique"] <= 6:
            charts.append(
                {
                    "kind": "pie",
                    "title": f"{col} — share",
                    "column": col,
                    "data": [{"label": str(t["value"]), "value": t["count"]} for t in summary["top"]],
                }
            )

    # Scatter of the two most-correlated numeric columns.
    if len(numeric_cols) >= 2:
        corr = _correlations(df[numeric_cols])
        if corr["top_pairs"]:
            a, b = corr["top_pairs"][0]["a"], corr["top_pairs"][0]["b"]
            sub = df[[a, b]].apply(pd.to_numeric, errors="coerce").dropna().head(2000)
            charts.append(
                {
                    "kind": "scatter",
                    "title": f"{a} vs {b} (r={corr['top_pairs'][0]['corr']:.2f})",
                    "x": a,
                    "y": b,
                    "data": [{"x": _finite(r[a]), "y": _finite(r[b])} for _, r in sub.iterrows()],
                }
            )

    # Line chart over the first datetime column vs the first numeric column.
    if datetime_cols and numeric_cols:
        dcol, ncol = datetime_cols[0], numeric_cols[0]
        sub = df[[dcol, ncol]].dropna().copy()
        sub[dcol] = pd.to_datetime(sub[dcol], errors="coerce")
        sub = sub.dropna().sort_values(dcol)
        if len(sub) >= 3:
            grouped = sub.groupby(sub[dcol].dt.to_period("M"))[ncol].mean()
            charts.append(
                {
                    "kind": "line",
                    "title": f"{ncol} over time (monthly mean)",
                    "x": dcol,
                    "y": ncol,
                    "data": [{"x": str(idx), "y": _finite(val)} for idx, val in grouped.items()],
                }
            )

    if len(numeric_cols) >= 2:
        corr = _correlations(df[numeric_cols])
        charts.append({"kind": "correlation_heatmap", "title": "Correlation heatmap", "data": corr})

    return charts


def _box_stats(numeric: pd.Series) -> dict[str, Any]:
    q1, q2, q3 = numeric.quantile(0.25), numeric.quantile(0.5), numeric.quantile(0.75)
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    whislo = float(numeric[numeric >= lo].min()) if (numeric >= lo).any() else float(numeric.min())
    whishi = float(numeric[numeric <= hi].max()) if (numeric <= hi).any() else float(numeric.max())
    outliers = numeric[(numeric < lo) | (numeric > hi)]
    return {
        "min": _finite(numeric.min()),
        "q1": _finite(q1),
        "median": _finite(q2),
        "q3": _finite(q3),
        "max": _finite(numeric.max()),
        "whisker_low": _finite(whislo),
        "whisker_high": _finite(whishi),
        "outlier_count": int(len(outliers)),
        "sample_outliers": [_finite(v) for v in outliers.head(20)],
    }


def _auto_insights(
    df: pd.DataFrame,
    kinds: dict[str, ColumnKind],
    numeric_summary: list[dict[str, Any]],
    categorical_summary: list[dict[str, Any]],
    correlations: dict[str, Any] | None,
    target: str | None,
) -> list[dict[str, Any]]:
    insights: list[dict[str, Any]] = []

    for ns in numeric_summary:
        skew = ns.get("skew") or 0.0
        if abs(skew) >= 1.0 and ns.get("count", 0) > 10:
            direction = "right" if skew > 0 else "left"
            insights.append(
                {
                    "category": "statistical",
                    "text": f"'{ns['column']}' is {direction}-skewed (skew = {skew:.2f}); a small number of {'high' if skew > 0 else 'low'} values pull the mean away from the median.",
                    "evidence": {"skew": skew, "mean": ns["mean"], "median": ns["median"]},
                }
            )

    for cs in categorical_summary:
        if cs["count"] and cs["top"]:
            top = cs["top"][0]
            if top["pct"] >= 80:
                insights.append(
                    {
                        "category": "data_quality",
                        "text": f"'{cs['column']}' is dominated by '{top['value']}' ({top['pct']:.1f}% of rows) — low variation limits its usefulness.",
                        "evidence": {"dominant_value": top["value"], "pct": top["pct"]},
                    }
                )

    if correlations and correlations["top_pairs"]:
        strong = [p for p in correlations["top_pairs"] if abs(p["corr"]) >= 0.6]
        for p in strong[:3]:
            insights.append(
                {
                    "category": "statistical",
                    "text": f"'{p['a']}' and '{p['b']}' are {'strongly ' if abs(p['corr']) >= 0.8 else ''}{'positively' if p['corr'] > 0 else 'negatively'} correlated (r = {p['corr']:.2f}) — they carry overlapping information.",
                    "evidence": {"corr": p["corr"]},
                }
            )

    if target and target in df.columns:
        tkind = kinds.get(target)
        if tkind in (ColumnKind.CATEGORICAL, ColumnKind.BOOLEAN):
            dist = df[target].value_counts(normalize=True)
            if not dist.empty:
                minority = dist.min() * 100
                if minority < 20:
                    insights.append(
                        {
                            "category": "ml",
                            "text": f"Target '{target}' is imbalanced — the minority class is {minority:.1f}% of rows. Prefer F1 / ROC-AUC over accuracy.",
                            "evidence": {"class_distribution": {str(k): round(float(v), 4) for k, v in dist.items()}},
                        }
                    )
            # Group differences for numeric features by target class.
            for ns in numeric_summary[:5]:
                col = ns["column"]
                grouped = df.groupby(target)[col].mean(numeric_only=True).dropna()
                if len(grouped) == 2:
                    lo_c, hi_c = grouped.idxmin(), grouped.idxmax()
                    lo_v, hi_v = float(grouped.min()), float(grouped.max())
                    if lo_v != 0 and abs(hi_v - lo_v) / (abs(lo_v) + 1e-9) > 0.25:
                        insights.append(
                            {
                                "category": "business",
                                "text": f"Mean '{col}' is {hi_v:.2f} for '{hi_c}' vs {lo_v:.2f} for '{lo_c}' — '{col}' is associated with '{target}'.",
                                "evidence": {"group_means": {str(k): round(float(v), 4) for k, v in grouped.items()}},
                            }
                        )

    if not insights:
        insights.append({"category": "data_quality", "text": "No strong skew, imbalance, or correlation stood out in the automated pass.", "evidence": {}})
    return insights


__all__ = ["run_eda"]
