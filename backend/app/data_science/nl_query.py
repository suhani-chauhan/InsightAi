"""Natural-language querying of an uploaded / in-memory dataset.

The LLM writes ONE read-only DuckDB SELECT against a single registered table
``data``; DuckDB runs it in-process over the DataFrame with external file /
network access disabled. A deterministic validator rejects anything that is
not a plain SELECT/WITH before it ever reaches the engine.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import pandas as pd
from langchain_core.messages import HumanMessage, SystemMessage

from app.data_science.dataset import Dataset, _json_safe_records
from app.db.models.llm import LlmExecutionContext
from app.integrations.llm_client import invoke_chat_llm

logger = logging.getLogger("insightai.data_science.nl_query")

MAX_RESULT_ROWS = 1000

_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|create|alter|attach|detach|copy|pragma|set|"
    r"install|load|export|import|call|read_csv|read_parquet|read_json|read_text|"
    r"glob|system|shell)\b|;|--|/\*",
    re.IGNORECASE,
)

_SYSTEM = (
    "You translate a question into ONE DuckDB SQL query over a single table named `data`. "
    "Rules: output ONLY the SQL, no prose, no markdown fences. It MUST be a single "
    "SELECT (optionally a leading WITH). No semicolons. Reference only the table `data`. "
    "Prefer explicit column names. Add LIMIT 200 unless the question is an aggregate. "
    "If the question cannot be answered from the columns, output exactly: NO_QUERY"
)


def _schema_prompt(df: pd.DataFrame) -> str:
    lines = []
    for col in df.columns:
        non_null = df[col].dropna()
        sample = ", ".join(repr(_json(v)) for v in non_null.head(3).tolist())
        lines.append(f"- {col} ({df[col].dtype}) e.g. {sample}")
    return "Table `data` columns:\n" + "\n".join(lines)


def _json(v: Any) -> Any:
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    return v


def _strip_sql(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", text).strip()
    return text.rstrip(";").strip()


def _validate(sql: str) -> str | None:
    low = sql.lstrip().lower()
    if not (low.startswith("select") or low.startswith("with")):
        return "The generated query was not a SELECT."
    if _FORBIDDEN.search(sql):
        return "The generated query contained a disallowed keyword."
    return None


def run_nl_query(dataset: Dataset, question: str, llm_context: LlmExecutionContext) -> dict[str, Any]:
    df = dataset.df
    user = f"{_schema_prompt(df)}\n\nQuestion: {question.strip()}"

    try:
        raw = invoke_chat_llm(
            llm_context,
            [SystemMessage(content=_SYSTEM), HumanMessage(content=user)],
            temperature=0,
            max_tokens=400,
        )
    except Exception as exc:  # noqa: BLE001
        logger.info("[nl-query] LLM unavailable: %s", exc)
        return {
            "answered": False,
            "reason": "The AI query layer needs an LLM credential and is unavailable right now.",
        }

    sql = _strip_sql(raw)
    if not sql or sql.upper().strip() == "NO_QUERY":
        return {"answered": False, "reason": "That question can't be answered from this dataset's columns."}

    err = _validate(sql)
    if err:
        return {"answered": False, "reason": err, "sql": sql}

    try:
        import duckdb

        con = duckdb.connect(config={"enable_external_access": False})
        con.register("data", df)
        result = con.execute(sql).fetch_df()
        con.close()
    except Exception as exc:  # noqa: BLE001
        return {"answered": False, "reason": f"The query failed: {str(exc).splitlines()[0][:200]}", "sql": sql}

    truncated = len(result) > MAX_RESULT_ROWS
    result = result.head(MAX_RESULT_ROWS)
    return {
        "answered": True,
        "sql": sql,
        "columns": [str(c) for c in result.columns],
        "rows": _json_safe_records(result),
        "row_count": int(len(result)),
        "truncated": truncated,
    }


__all__ = ["run_nl_query", "MAX_RESULT_ROWS"]
