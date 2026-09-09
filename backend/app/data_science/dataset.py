"""Dataset wrapper and column-type classification.

A :class:`Dataset` is a thin, immutable-ish envelope around a pandas
``DataFrame`` plus provenance metadata (where the rows came from). It also
owns the single source of truth for *column kinds* — numeric / categorical /
datetime / boolean — which every downstream module (profiling, quality, EDA,
ML preprocessing) relies on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable

import numpy as np
import pandas as pd

# Guardrails — analysis always runs on a bounded in-memory copy (master spec §17/§49).
MAX_ANALYSIS_ROWS = 50_000
MAX_ANALYSIS_COLUMNS = 200


class ColumnKind(str, Enum):
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    TEXT = "text"
    EMPTY = "empty"


@dataclass
class Dataset:
    """Bounded analysis copy of a tabular result."""

    df: pd.DataFrame
    name: str = "dataset"
    source: str = "query_result"
    source_detail: dict[str, Any] = field(default_factory=dict)
    sampled: bool = False
    original_row_count: int | None = None

    # ------------------------------------------------------------------ build
    @classmethod
    def from_records(
        cls,
        columns: Iterable[str],
        rows: list[dict[str, Any]] | list[list[Any]],
        *,
        name: str = "dataset",
        source: str = "query_result",
        source_detail: dict[str, Any] | None = None,
    ) -> "Dataset":
        cols = [str(c) for c in columns]
        if rows and isinstance(rows[0], dict):
            df = pd.DataFrame(rows, columns=cols)
        else:
            df = pd.DataFrame(rows, columns=cols)

        original = len(df)
        sampled = False
        if len(df) > MAX_ANALYSIS_ROWS:
            df = df.sample(MAX_ANALYSIS_ROWS, random_state=42).reset_index(drop=True)
            sampled = True
        if df.shape[1] > MAX_ANALYSIS_COLUMNS:
            df = df.iloc[:, :MAX_ANALYSIS_COLUMNS]

        df = _coerce_types(df)
        return cls(
            df=df,
            name=name or "dataset",
            source=source,
            source_detail=source_detail or {},
            sampled=sampled,
            original_row_count=original,
        )

    def copy(self) -> "Dataset":
        return Dataset(
            df=self.df.copy(deep=True),
            name=self.name,
            source=self.source,
            source_detail=dict(self.source_detail),
            sampled=self.sampled,
            original_row_count=self.original_row_count,
        )

    def with_df(self, df: pd.DataFrame) -> "Dataset":
        clone = self.copy()
        clone.df = df.reset_index(drop=True)
        return clone

    # ------------------------------------------------------------- introspect
    @property
    def n_rows(self) -> int:
        return int(len(self.df))

    @property
    def n_cols(self) -> int:
        return int(self.df.shape[1])

    def column_kinds(self) -> dict[str, ColumnKind]:
        return {col: classify_column(self.df[col]) for col in self.df.columns}

    def columns_of_kind(self, *kinds: ColumnKind) -> list[str]:
        wanted = set(kinds)
        return [c for c, k in self.column_kinds().items() if k in wanted]

    def sample_rows(self, n: int = 10) -> list[dict[str, Any]]:
        head = self.df.head(n)
        return _json_safe_records(head)

    def overview(self) -> dict[str, Any]:
        kinds = self.column_kinds()
        return {
            "name": self.name,
            "source": self.source,
            "source_detail": self.source_detail,
            "n_rows": self.n_rows,
            "n_cols": self.n_cols,
            "sampled": self.sampled,
            "original_row_count": self.original_row_count,
            "columns": [
                {
                    "name": col,
                    "kind": kinds[col].value,
                    "dtype": str(self.df[col].dtype),
                    "missing": int(self.df[col].isna().sum()),
                }
                for col in self.df.columns
            ],
            "sample_rows": self.sample_rows(10),
        }


# ---------------------------------------------------------------------- helpers
def _coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    """Best-effort recovery of datetimes stored as strings.

    Numeric-string recovery is deliberately *not* done here — that is a data
    quality finding the user should approve (master spec §8), not a silent
    coercion.
    """
    out = df.copy()
    for col in out.columns:
        s = out[col]
        if s.dtype != object:
            continue
        non_null = s.dropna()
        if non_null.empty:
            continue
        sample = non_null.astype(str).head(50)
        looks_datey = sample.str.contains(r"\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}", regex=True).mean()
        if looks_datey >= 0.8:
            parsed = pd.to_datetime(s, errors="coerce")
            if parsed.notna().mean() >= 0.8:
                out[col] = parsed
    return out


def classify_column(s: pd.Series) -> ColumnKind:
    non_null = s.dropna()
    if non_null.empty:
        return ColumnKind.EMPTY

    if pd.api.types.is_bool_dtype(s):
        return ColumnKind.BOOLEAN
    if pd.api.types.is_datetime64_any_dtype(s):
        return ColumnKind.DATETIME
    if pd.api.types.is_numeric_dtype(s):
        uniques = set(pd.unique(non_null))
        if uniques.issubset({0, 1}) and len(uniques) <= 2:
            return ColumnKind.BOOLEAN
        return ColumnKind.NUMERIC

    # object / string
    lowered = non_null.astype(str).str.strip().str.lower()
    if set(lowered.unique()).issubset({"true", "false", "yes", "no", "y", "n", "0", "1", "t", "f"}):
        return ColumnKind.BOOLEAN

    nunique = non_null.nunique()
    n = len(non_null)
    avg_len = non_null.astype(str).str.len().mean()
    # Free text: many uniques and long-ish values.
    if nunique > max(50, 0.6 * n) and avg_len > 40:
        return ColumnKind.TEXT
    return ColumnKind.CATEGORICAL


def _json_safe_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    records = df.to_dict(orient="records")
    return [{k: _json_safe(v) for k, v in row.items()} for row in records]


def _json_safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        f = float(value)
        return None if (np.isnan(f) or np.isinf(f)) else f
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if value is pd.NaT:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


__all__ = [
    "Dataset",
    "ColumnKind",
    "classify_column",
    "MAX_ANALYSIS_ROWS",
    "MAX_ANALYSIS_COLUMNS",
    "_json_safe",
    "_json_safe_records",
]
