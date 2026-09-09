"""InsightAI — Data Science workspace.

Deterministic data-intelligence engine built on pandas / numpy / scikit-learn.

Design rule (see master spec §43/§69): every number surfaced to the user —
statistics, quality scores, cleaning impact, model metrics, feature importance —
is computed here in Python. The LLM layer (``insights_llm``) only *explains*
values that this package has already computed.
"""

from app.data_science.dataset import Dataset, ColumnKind
from app.data_science.profiling import profile_dataset
from app.data_science.quality import analyze_quality, quality_score
from app.data_science.cleaning import (
    CleaningSession,
    recommend_cleaning,
    apply_operations,
    CLEANING_OPERATIONS,
)
from app.data_science.eda import run_eda
from app.data_science.ml import detect_task, train_and_compare, predict_with_bundle
from app.data_science.nl_query import run_nl_query
from app.data_science.report import build_report

__all__ = [
    "Dataset",
    "ColumnKind",
    "profile_dataset",
    "analyze_quality",
    "quality_score",
    "CleaningSession",
    "recommend_cleaning",
    "apply_operations",
    "CLEANING_OPERATIONS",
    "run_eda",
    "run_nl_query",
    "detect_task",
    "train_and_compare",
    "predict_with_bundle",
    "build_report",
]
