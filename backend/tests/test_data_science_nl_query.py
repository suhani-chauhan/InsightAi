"""Natural-language data query over an uploaded dataset (DuckDB, read-only)."""

import pandas as pd
import pytest

from app.data_science import nl_query as mod
from app.data_science.dataset import Dataset
from app.db.models.llm import LlmExecutionContext


def _ctx() -> LlmExecutionContext:
    return LlmExecutionContext(owner_id="u1", feature="data_science_query", interaction_type="explicit")


@pytest.fixture
def sales() -> Dataset:
    df = pd.DataFrame(
        {
            "region": ["North", "South", "North", "East", "South", "North"],
            "product": ["A", "B", "A", "C", "A", "B"],
            "units": [10, 4, 7, 2, 9, 5],
            "revenue": [1000, 800, 700, 300, 900, 600],
        }
    )
    return Dataset.from_records(df.columns, df.to_dict("records"), name="sales.csv", source="upload")


def _patch_llm(monkeypatch, sql: str):
    monkeypatch.setattr(mod, "invoke_chat_llm", lambda *a, **k: sql)


def test_valid_aggregate_query_runs(monkeypatch, sales):
    _patch_llm(monkeypatch, "SELECT region, SUM(revenue) AS total FROM data GROUP BY region ORDER BY total DESC")
    out = mod.run_nl_query(sales, "total revenue per region", _ctx())
    assert out["answered"] is True
    assert out["columns"] == ["region", "total"]
    top = out["rows"][0]
    assert top["region"] == "North" and top["total"] == 2300


def test_markdown_fenced_sql_is_stripped(monkeypatch, sales):
    _patch_llm(monkeypatch, "```sql\nSELECT COUNT(*) AS n FROM data\n```")
    out = mod.run_nl_query(sales, "how many rows", _ctx())
    assert out["answered"] is True and out["rows"][0]["n"] == 6


def test_no_query_sentinel(monkeypatch, sales):
    _patch_llm(monkeypatch, "NO_QUERY")
    out = mod.run_nl_query(sales, "what is the meaning of life", _ctx())
    assert out["answered"] is False


def test_non_select_is_rejected(monkeypatch, sales):
    _patch_llm(monkeypatch, "UPDATE data SET revenue = 0")
    out = mod.run_nl_query(sales, "zero out revenue", _ctx())
    assert out["answered"] is False
    assert "select" in out["reason"].lower()


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM data; DROP TABLE data",
        "SELECT * FROM read_csv_auto('/etc/passwd')",
        "ATTACH 'evil.db'; SELECT 1",
        "SELECT * FROM data -- comment",
        "COPY data TO 'out.csv'",
    ],
)
def test_dangerous_sql_is_blocked(monkeypatch, sales, sql):
    _patch_llm(monkeypatch, sql)
    out = mod.run_nl_query(sales, "x", _ctx())
    assert out["answered"] is False


def test_broken_sql_fails_gracefully(monkeypatch, sales):
    _patch_llm(monkeypatch, "SELECT nonexistent_column FROM data")
    out = mod.run_nl_query(sales, "x", _ctx())
    assert out["answered"] is False
    assert "failed" in out["reason"].lower()


def test_llm_unavailable_is_reported(monkeypatch, sales):
    def boom(*a, **k):
        raise RuntimeError("no credential")

    monkeypatch.setattr(mod, "invoke_chat_llm", boom)
    out = mod.run_nl_query(sales, "total revenue", _ctx())
    assert out["answered"] is False
    assert "unavailable" in out["reason"].lower()


def test_result_row_cap(monkeypatch):
    df = pd.DataFrame({"n": range(5000)})
    ds = Dataset.from_records(df.columns, df.to_dict("records"), name="big", source="upload")
    _patch_llm(monkeypatch, "SELECT n FROM data")
    out = mod.run_nl_query(ds, "all rows", _ctx())
    assert out["answered"] is True
    assert out["row_count"] == mod.MAX_RESULT_ROWS
    assert out["truncated"] is True
