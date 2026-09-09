"""Assemble a structured Data Science report (master spec §38 / §60).

The report is a plain dict of already-computed artifacts. Rendering (HTML/PDF)
is the frontend's job; this module guarantees the *content* is grounded.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def build_report(
    *,
    dataset_overview: dict[str, Any],
    profile: dict[str, Any] | None,
    quality: dict[str, Any] | None,
    cleaning: dict[str, Any] | None,
    eda: dict[str, Any] | None,
    ml: dict[str, Any] | None,
    narrative: str | None = None,
) -> dict[str, Any]:
    sections: list[dict[str, Any]] = []

    sections.append(
        {
            "id": "overview",
            "title": "Dataset Overview",
            "body": {
                "name": dataset_overview.get("name"),
                "rows": dataset_overview.get("n_rows"),
                "columns": dataset_overview.get("n_cols"),
                "sampled": dataset_overview.get("sampled"),
                "column_kinds": _kind_counts(dataset_overview),
            },
        }
    )

    if quality:
        score = quality.get("score", {})
        sections.append(
            {
                "id": "quality",
                "title": "Data Quality",
                "body": {
                    "overall_score": score.get("overall"),
                    "grade": score.get("grade"),
                    "dimensions": score.get("dimensions", []),
                    "issue_count": quality.get("issue_count", 0),
                    "top_issues": [
                        {"title": i["title"], "severity": i["severity"], "recommendation": i["recommendation"]}
                        for i in quality.get("issues", [])[:8]
                    ],
                },
            }
        )

    if cleaning and cleaning.get("steps"):
        before = cleaning.get("original", {})
        after = cleaning.get("current", {})
        sections.append(
            {
                "id": "cleaning",
                "title": "Cleaning Operations",
                "body": {
                    "operations": [rec for step in cleaning["steps"] for rec in step.get("records", [])],
                    "before": before,
                    "after": after,
                    "quality_before": cleaning.get("quality_before"),
                    "quality_after": cleaning.get("quality_after"),
                },
            }
        )

    if eda:
        sections.append(
            {
                "id": "eda",
                "title": "Exploratory Analysis",
                "body": {
                    "numeric_summary": eda.get("numeric_summary", []),
                    "categorical_summary": eda.get("categorical_summary", []),
                    "top_correlations": (eda.get("correlations") or {}).get("top_pairs", []),
                    "insights": eda.get("insights", []),
                    "chart_count": len(eda.get("charts", [])),
                },
            }
        )

    if ml:
        sections.append(
            {
                "id": "ml",
                "title": "Machine Learning",
                "body": {
                    "task": ml.get("task"),
                    "target": ml.get("target"),
                    "primary_metric": ml.get("primary_metric"),
                    "best_model": ml.get("best_model_name"),
                    "comparison": ml.get("comparison", []),
                    "metrics": ml.get("metrics", {}),
                    "feature_importance": ml.get("feature_importance", [])[:10],
                    "n_train": ml.get("n_train"),
                    "n_test": ml.get("n_test"),
                    "warnings": ml.get("warnings", []),
                },
            }
        )

    recommendations = _recommendations(quality, cleaning, eda, ml)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "title": f"InsightAI — {dataset_overview.get('name', 'Dataset')} report",
        "executive_summary": narrative or _fallback_summary(dataset_overview, quality, eda, ml),
        "sections": sections,
        "recommendations": recommendations,
    }


def _kind_counts(overview: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for col in overview.get("columns", []):
        counts[col["kind"]] = counts.get(col["kind"], 0) + 1
    return counts


def _fallback_summary(overview, quality, eda, ml) -> str:
    parts = [
        f"The dataset '{overview.get('name', 'dataset')}' has {overview.get('n_rows', 0):,} rows and {overview.get('n_cols', 0)} columns."
    ]
    if quality:
        s = quality.get("score", {})
        parts.append(f"Data quality scores {s.get('overall')}/100 ({s.get('grade')}), with {quality.get('issue_count', 0)} issue(s) detected.")
    if eda and eda.get("insights"):
        parts.append(eda["insights"][0]["text"])
    if ml:
        parts.append(
            f"For predicting '{ml.get('target')}' ({ml.get('task')}), {ml.get('best_model_name')} performed best "
            f"on {ml.get('primary_metric')}."
        )
    return " ".join(parts)


def _recommendations(quality, cleaning, eda, ml) -> list[str]:
    recs: list[str] = []
    if quality:
        highs = [i for i in quality.get("issues", []) if i["severity"] == "high"]
        for i in highs[:4]:
            recs.append(i["recommendation"])
    if ml and ml.get("feature_importance"):
        top = ml["feature_importance"][0]["feature"]
        recs.append(f"'{top}' was the strongest predictor — prioritise data collection and quality for this field.")
    if eda:
        for ins in eda.get("insights", []):
            if ins["category"] == "ml":
                recs.append(ins["text"])
                break
    if not recs:
        recs.append("No high-severity issues found — the dataset is in good shape for analysis.")
    return recs


__all__ = ["build_report"]
