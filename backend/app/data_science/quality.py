"""Data quality engine + explainable quality score (master spec §8 / §9).

Every issue carries a stable ``code``, a ``severity`` (info | low | medium |
high), the affected column(s), computed evidence, and a plain-language
``recommendation`` string. The quality score is a deterministic function of
the issues found — no LLM, no random numbers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from app.data_science.dataset import ColumnKind, Dataset

SEVERITY_ORDER = {"info": 0, "low": 1, "medium": 2, "high": 3}

# Score dimensions and how much each can subtract from 100.
_DIMENSIONS = {
    "missing_values": "Missing Values",
    "duplicates": "Duplicates",
    "data_types": "Data Types",
    "categorical_consistency": "Categorical Consistency",
    "outliers": "Outliers",
    "constant_columns": "Constant Columns",
    "potential_leakage": "Potential Leakage",
}


@dataclass
class QualityIssue:
    code: str
    dimension: str
    severity: str
    title: str
    columns: list[str]
    evidence: dict[str, Any]
    recommendation: str
    suggested_operation: dict[str, Any] | None = field(default=None)

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "dimension": self.dimension,
            "severity": self.severity,
            "title": self.title,
            "columns": self.columns,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
            "suggested_operation": self.suggested_operation,
        }


def analyze_quality(dataset: Dataset) -> dict[str, Any]:
    df = dataset.df
    kinds = dataset.column_kinds()
    n_rows = len(df)
    issues: list[QualityIssue] = []

    issues += _missing_value_issues(df, n_rows)
    issues += _duplicate_issues(df, n_rows)
    issues += _type_issues(df, kinds)
    issues += _categorical_consistency_issues(df, kinds)
    issues += _outlier_issues(df, kinds)
    issues += _constant_issues(df, kinds, n_rows)
    issues += _leakage_issues(df, kinds)

    issues.sort(key=lambda i: SEVERITY_ORDER[i.severity], reverse=True)
    score = quality_score(issues, dataset)

    return {
        "score": score,
        "issue_count": len(issues),
        "issues": [i.as_dict() for i in issues],
    }


# --------------------------------------------------------------- missing values
def _missing_value_issues(df: pd.DataFrame, n_rows: int) -> list[QualityIssue]:
    out: list[QualityIssue] = []
    for col in df.columns:
        miss = int(df[col].isna().sum())
        if miss == 0:
            continue
        pct = 100.0 * miss / n_rows if n_rows else 0.0
        if miss == n_rows:
            sev, rec, op = "high", "Column is completely empty — drop it.", {"op": "drop_column", "params": {"column": col}}
        elif pct >= 40:
            sev, rec, op = "high", f"{pct:.1f}% missing — consider dropping the column or the affected rows.", {"op": "drop_column", "params": {"column": col}}
        elif pct >= 5:
            sev, rec, op = "medium", f"{pct:.1f}% missing — impute using a strategy matched to the column.", {"op": "impute_missing", "params": {"column": col, "strategy": "auto"}}
        else:
            sev, rec, op = "low", f"{pct:.1f}% missing — safe to impute.", {"op": "impute_missing", "params": {"column": col, "strategy": "auto"}}
        out.append(
            QualityIssue(
                code=f"missing::{col}",
                dimension="missing_values",
                severity=sev,
                title=f"'{col}' has missing values",
                columns=[col],
                evidence={"missing": miss, "missing_pct": round(pct, 2)},
                recommendation=rec,
                suggested_operation=op,
            )
        )
    return out


# ------------------------------------------------------------------- duplicates
def _duplicate_issues(df: pd.DataFrame, n_rows: int) -> list[QualityIssue]:
    out: list[QualityIssue] = []
    dup = int(df.duplicated(keep=False).sum())
    if dup:
        pct = 100.0 * dup / n_rows if n_rows else 0.0
        out.append(
            QualityIssue(
                code="duplicates::rows",
                dimension="duplicates",
                severity="high" if pct >= 5 else "medium" if pct >= 1 else "low",
                title="Exact duplicate rows",
                columns=[],
                evidence={"duplicate_rows": dup, "duplicate_pct": round(pct, 2)},
                recommendation=f"{dup} fully duplicated rows detected — review, then remove keeping the first occurrence.",
                suggested_operation={"op": "drop_duplicates", "params": {"keep": "first"}},
            )
        )

    # Candidate id columns with repeated values.
    for col in df.columns:
        name = str(col).lower()
        if not (name == "id" or name.endswith("_id") or name.endswith("id") and df[col].dtype != object):
            continue
        non_null = df[col].dropna()
        if non_null.empty:
            continue
        dup_ids = int(non_null.duplicated(keep=False).sum())
        if dup_ids:
            out.append(
                QualityIssue(
                    code=f"duplicates::id::{col}",
                    dimension="duplicates",
                    severity="medium",
                    title=f"Identifier '{col}' is not unique",
                    columns=[col],
                    evidence={"duplicate_values": dup_ids},
                    recommendation=f"'{col}' looks like an identifier but has {dup_ids} repeated values — investigate before modelling.",
                    suggested_operation=None,
                )
            )
    return out


# ------------------------------------------------------------------ data types
_NUMERIC_RE = re.compile(r"^-?\d{1,3}(,\d{3})*(\.\d+)?$|^-?\d*\.?\d+$")


def _type_issues(df: pd.DataFrame, kinds: dict[str, ColumnKind]) -> list[QualityIssue]:
    out: list[QualityIssue] = []
    for col, kind in kinds.items():
        if kind not in (ColumnKind.CATEGORICAL, ColumnKind.TEXT):
            continue
        s = df[col].dropna().astype(str).str.strip()
        if s.empty:
            continue
        numeric_like = s.str.match(_NUMERIC_RE).mean()
        if numeric_like >= 0.9:
            out.append(
                QualityIssue(
                    code=f"dtype::numeric_string::{col}",
                    dimension="data_types",
                    severity="medium",
                    title=f"'{col}' holds numbers stored as text",
                    columns=[col],
                    evidence={"numeric_like_pct": round(100 * numeric_like, 2)},
                    recommendation=f"Convert '{col}' to a numeric type before analysis or modelling.",
                    suggested_operation={"op": "to_numeric", "params": {"column": col}},
                )
            )
            continue
        date_like = s.str.contains(r"\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}", regex=True).mean()
        if date_like >= 0.9:
            out.append(
                QualityIssue(
                    code=f"dtype::date_string::{col}",
                    dimension="data_types",
                    severity="low",
                    title=f"'{col}' holds dates stored as text",
                    columns=[col],
                    evidence={"date_like_pct": round(100 * date_like, 2)},
                    recommendation=f"Parse '{col}' as a datetime to enable time-based analysis.",
                    suggested_operation={"op": "to_datetime", "params": {"column": col}},
                )
            )
    return out


# ----------------------------------------------------- categorical consistency
def _canonical(value: str) -> str:
    return re.sub(r"\s+", " ", str(value).strip().lower())


def _categorical_consistency_issues(df: pd.DataFrame, kinds: dict[str, ColumnKind]) -> list[QualityIssue]:
    out: list[QualityIssue] = []
    for col, kind in kinds.items():
        if kind != ColumnKind.CATEGORICAL:
            continue
        s = df[col].dropna().astype(str)
        if s.empty:
            continue
        raw_levels = s.unique().tolist()
        if len(raw_levels) > 200:
            continue
        groups: dict[str, list[str]] = {}
        for level in raw_levels:
            groups.setdefault(_canonical(level), []).append(level)
        collisions = {k: v for k, v in groups.items() if len(v) > 1}
        ws_only = [lv for lv in raw_levels if lv != lv.strip()]
        if collisions:
            examples = [v for v in list(collisions.values())[:5]]
            out.append(
                QualityIssue(
                    code=f"category::inconsistent::{col}",
                    dimension="categorical_consistency",
                    severity="medium",
                    title=f"'{col}' has inconsistent category labels",
                    columns=[col],
                    evidence={
                        "raw_level_count": len(raw_levels),
                        "canonical_level_count": len(groups),
                        "examples": examples,
                    },
                    recommendation=(
                        f"{len(collisions)} groups of labels in '{col}' differ only by case or spacing "
                        f"(e.g. {examples[0]}). Standardise them to a single canonical label."
                    ),
                    suggested_operation={"op": "standardize_categories", "params": {"column": col}},
                )
            )
        elif ws_only:
            out.append(
                QualityIssue(
                    code=f"category::whitespace::{col}",
                    dimension="categorical_consistency",
                    severity="low",
                    title=f"'{col}' has leading/trailing whitespace",
                    columns=[col],
                    evidence={"affected_levels": ws_only[:10]},
                    recommendation=f"Trim whitespace in '{col}'.",
                    suggested_operation={"op": "trim_whitespace", "params": {"column": col}},
                )
            )
    return out


# --------------------------------------------------------------------- outliers
def _outlier_issues(df: pd.DataFrame, kinds: dict[str, ColumnKind]) -> list[QualityIssue]:
    out: list[QualityIssue] = []
    for col, kind in kinds.items():
        if kind != ColumnKind.NUMERIC:
            continue
        numeric = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(numeric) < 12 or numeric.nunique() < 5:
            continue
        q1, q3 = numeric.quantile(0.25), numeric.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        mask = (numeric < lower) | (numeric > upper)
        n_out = int(mask.sum())
        if n_out == 0:
            continue
        pct = 100.0 * n_out / len(numeric)
        med = float(numeric.median())
        mad = float((numeric - med).abs().median()) or 1e-9
        mod_z = 0.6745 * (numeric - med).abs() / mad
        out.append(
            QualityIssue(
                code=f"outliers::{col}",
                dimension="outliers",
                severity="medium" if pct >= 5 else "low",
                title=f"'{col}' contains outliers",
                columns=[col],
                evidence={
                    "iqr_outliers": n_out,
                    "outlier_pct": round(pct, 2),
                    "modified_zscore_outliers": int((mod_z > 3.5).sum()),
                    "lower_fence": round(float(lower), 4),
                    "upper_fence": round(float(upper), 4),
                },
                recommendation=(
                    f"{n_out} values in '{col}' fall outside 1.5×IQR. Outliers can be real business "
                    "events — review before deciding to keep, cap, or remove them."
                ),
                suggested_operation={"op": "handle_outliers", "params": {"column": col, "strategy": "flag"}},
            )
        )
    return out


# ---------------------------------------------------------- constant / low-var
def _constant_issues(df: pd.DataFrame, kinds: dict[str, ColumnKind], n_rows: int) -> list[QualityIssue]:
    out: list[QualityIssue] = []
    for col in df.columns:
        non_null = df[col].dropna()
        if non_null.empty:
            continue
        nunique = non_null.nunique()
        if nunique <= 1:
            out.append(
                QualityIssue(
                    code=f"constant::{col}",
                    dimension="constant_columns",
                    severity="low",
                    title=f"'{col}' is constant",
                    columns=[col],
                    evidence={"unique_values": int(nunique)},
                    recommendation=f"'{col}' has a single value and carries no signal — drop it.",
                    suggested_operation={"op": "drop_column", "params": {"column": col}},
                )
            )
            continue
        dominance = non_null.value_counts(normalize=True).iloc[0]
        if dominance >= 0.98 and kinds.get(col) != ColumnKind.BOOLEAN:
            out.append(
                QualityIssue(
                    code=f"near_constant::{col}",
                    dimension="constant_columns",
                    severity="info",
                    title=f"'{col}' is near-constant",
                    columns=[col],
                    evidence={"dominant_value_pct": round(float(dominance) * 100, 2)},
                    recommendation=f"{dominance*100:.1f}% of '{col}' is one value — it may add little predictive value.",
                    suggested_operation=None,
                )
            )
    return out


# --------------------------------------------------------------------- leakage
_LEAKAGE_HINTS = ("prediction", "predicted", "score", "probability", "outcome", "target", "label", "churned", "is_fraud", "future")


def _leakage_issues(df: pd.DataFrame, kinds: dict[str, ColumnKind]) -> list[QualityIssue]:
    out: list[QualityIssue] = []
    for col in df.columns:
        name = str(col).lower()
        if any(h in name for h in _LEAKAGE_HINTS):
            out.append(
                QualityIssue(
                    code=f"leakage::name::{col}",
                    dimension="potential_leakage",
                    severity="info",
                    title=f"'{col}' may leak the target",
                    columns=[col],
                    evidence={"reason": "name suggests a post-outcome or target-derived field"},
                    recommendation=(
                        f"Review '{col}' before modelling — if it is only known *after* the outcome, "
                        "excluding it prevents data leakage."
                    ),
                    suggested_operation=None,
                )
            )
    return out


# ----------------------------------------------------------------------- score
def quality_score(issues: list[QualityIssue], dataset: Dataset) -> dict[str, Any]:
    """Deterministic 0–100 score with a per-dimension breakdown.

    Each dimension starts at 100 and loses points per issue, weighted by
    severity. The overall score is the mean of the dimension scores.
    """
    penalties = {"info": 2, "low": 6, "medium": 16, "high": 34}
    dim_scores = {key: 100.0 for key in _DIMENSIONS}
    dim_reasons: dict[str, list[str]] = {key: [] for key in _DIMENSIONS}

    for issue in issues:
        dim = issue.dimension
        if dim not in dim_scores:
            continue
        dim_scores[dim] = max(0.0, dim_scores[dim] - penalties[issue.severity])
        dim_reasons[dim].append(issue.title)

    overall = round(sum(dim_scores.values()) / len(dim_scores), 1)
    return {
        "overall": overall,
        "grade": _grade(overall),
        "dimensions": [
            {
                "key": key,
                "label": label,
                "score": round(dim_scores[key], 1),
                "issues": dim_reasons[key],
            }
            for key, label in _DIMENSIONS.items()
        ],
    }


def _grade(score: float) -> str:
    if score >= 90:
        return "excellent"
    if score >= 75:
        return "good"
    if score >= 60:
        return "fair"
    if score >= 40:
        return "poor"
    return "critical"


__all__ = ["analyze_quality", "quality_score", "QualityIssue", "SEVERITY_ORDER"]
