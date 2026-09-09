"""Orchestration for the InsightMind AI Data Science workspace.

Sessions are held **in memory** (bounded LRU + TTL), scoped to the owning user.
They deliberately do not touch the connected production database — a session is
an analysis copy of a query result (master spec §17). Trade-off: sessions do
not survive a process restart and are not shared across worker processes; that
is acceptable for the synchronous, single-analyst workflow this ships with.
"""

from __future__ import annotations

import io
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from app.core.errors import BadRequestError, NotFoundError
from app.data_science import (
    Dataset,
    analyze_quality,
    build_report,
    detect_task,
    profile_dataset,
    recommend_cleaning,
    run_eda,
    train_and_compare,
)
from app.data_science.cleaning import CleaningSession
from app.data_science.demo_data import DEMO_NAME, DEMO_TARGET, build_demo_dataframe
from app.data_science.ml import TrainedModelBundle, predict_with_bundle
from app.data_science import insights_llm
from app.db.models.llm import LlmExecutionContext

_MAX_SESSIONS_PER_USER = 8
_SESSION_TTL_SECONDS = 60 * 60 * 3  # 3 hours
_MAX_INBOUND_ROWS = 100_000


@dataclass
class AnalysisSession:
    id: str
    user_id: str
    dataset: Dataset
    cleaning: CleaningSession
    created_at: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    cache: dict[str, Any] = field(default_factory=dict)
    model_bundle: TrainedModelBundle | None = None

    def touch(self) -> None:
        self.last_seen = time.time()

    @property
    def working(self) -> Dataset:
        """Dataset with the current (post-cleaning) frame."""
        return self.dataset.with_df(self.cleaning.current)


class _SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, AnalysisSession] = {}
        self._lock = threading.RLock()

    def _evict(self) -> None:
        now = time.time()
        stale = [sid for sid, s in self._sessions.items() if now - s.last_seen > _SESSION_TTL_SECONDS]
        for sid in stale:
            self._sessions.pop(sid, None)

    def add(self, session: AnalysisSession) -> None:
        with self._lock:
            self._evict()
            owned = sorted(
                (s for s in self._sessions.values() if s.user_id == session.user_id),
                key=lambda s: s.last_seen,
            )
            while len(owned) >= _MAX_SESSIONS_PER_USER:
                victim = owned.pop(0)
                self._sessions.pop(victim.id, None)
            self._sessions[session.id] = session

    def get(self, session_id: str, user_id: str) -> AnalysisSession:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None or session.user_id != user_id:
                raise NotFoundError("Analysis session not found or has expired.")
            session.touch()
            return session

    def list_for_user(self, user_id: str) -> list[AnalysisSession]:
        with self._lock:
            self._evict()
            return sorted(
                (s for s in self._sessions.values() if s.user_id == user_id),
                key=lambda s: s.last_seen,
                reverse=True,
            )


_store = _SessionStore()


# --------------------------------------------------------------- session build
def create_session_from_records(
    user_id: str,
    *,
    columns: list[str],
    rows: list[dict[str, Any]],
    name: str | None = None,
    source: str = "query_result",
    source_detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not columns:
        raise BadRequestError("The dataset has no columns.")
    if not rows:
        raise BadRequestError("The dataset has no rows to analyse.")
    if len(rows) > _MAX_INBOUND_ROWS:
        raise BadRequestError(
            f"This result has {len(rows):,} rows. Narrow the query to {_MAX_INBOUND_ROWS:,} rows or fewer before analysing."
        )

    dataset = Dataset.from_records(
        columns, rows, name=name or "Query result", source=source, source_detail=source_detail or {}
    )
    return _register(user_id, dataset)


def create_session_from_text(
    user_id: str,
    *,
    name: str,
    content: str,
    fmt: str = "csv",
    delimiter: str | None = None,
) -> dict[str, Any]:
    """Parse an uploaded delimited-text file into an analysis session."""
    # Deterministic delimiter choice — csv.Sniffer misfires badly on 1-column data.
    if delimiter:
        candidates = [delimiter]
    elif fmt == "tsv":
        candidates = ["\t"]
    else:
        first_line = content.splitlines()[0] if content.strip() else ""
        candidates = [","]
        for alt in (";", "\t", "|"):
            if alt in first_line and "," not in first_line:
                candidates = [alt]
                break

    df = None
    parse_error: Exception | None = None
    for sep in candidates:
        try:
            parsed = pd.read_csv(io.StringIO(content), sep=sep, skip_blank_lines=True)
        except Exception as exc:  # noqa: BLE001
            parse_error = exc
            continue
        df = parsed
        break
    if df is None:
        raise BadRequestError(
            f"Could not parse the file as {fmt.upper()}: {parse_error}" if parse_error else "Could not parse the file."
        )

    df = df.dropna(axis=1, how="all")
    df.columns = [str(c).strip() for c in df.columns]
    if df.shape[1] == 0:
        raise BadRequestError("The file has no readable columns.")
    if df.shape[1] == 1 and any(ch in str(df.columns[0]) for ch in (";", "\t", "|", ",")):
        raise BadRequestError(
            "Only one column was detected but the header still contains a separator — check the file's "
            "delimiter (comma vs. semicolon vs. tab)."
        )
    if len(df) == 0:
        raise BadRequestError("The file has a header but no data rows.")
    if len(df) > _MAX_INBOUND_ROWS:
        raise BadRequestError(
            f"The file has {len(df):,} rows. Trim it to {_MAX_INBOUND_ROWS:,} rows or fewer before uploading."
        )

    dataset = Dataset.from_records(
        df.columns.tolist(),
        df.to_dict("records"),
        name=name.strip() or "Uploaded dataset",
        source="upload",
        source_detail={"format": fmt, "original_columns": df.shape[1]},
    )
    return _register(user_id, dataset)


_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]{0,62}$")
_MAX_TABLE_ROWS = 20_000


def _safe_identifier(value: str, kind: str) -> str:
    value = (value or "").strip().strip('"')
    if not _IDENTIFIER_RE.match(value):
        raise BadRequestError(f"Invalid {kind} name: {value!r}. Only letters, digits and underscore are allowed.")
    return value


async def create_session_from_table(
    user_id: str,
    *,
    connection_id: str,
    table: str,
    schema: str | None = None,
    limit: int = 5_000,
) -> dict[str, Any]:
    """Pull a bounded, read-only sample of a database table into a session.

    Runs through the existing query engine, so read-only enforcement, statement
    timeouts, connection-scope checks and row limits all apply. The source table
    is only ever read.
    """
    from app.services.query_execution_service import execute_for_connection

    table_id = _safe_identifier(table, "table")
    qualified = f'"{table_id}"'
    if schema:
        schema_id = _safe_identifier(schema, "schema")
        qualified = f'"{schema_id}".{qualified}'

    row_limit = max(1, min(int(limit), _MAX_TABLE_ROWS))
    sql = f"SELECT * FROM {qualified} LIMIT {row_limit}"

    try:
        result = await execute_for_connection(user_id, connection_id, sql, row_limit=row_limit, readonly=True)
    except ValueError as exc:
        raise BadRequestError(str(exc)) from exc

    if not result.success:
        raise BadRequestError(result.error or "The table could not be read.")
    if not result.rows:
        raise BadRequestError(f"'{table_id}' returned no rows.")

    dataset = Dataset.from_records(
        result.columns,
        result.rows,
        name=table_id,
        source="database_table",
        source_detail={
            "connection_id": connection_id,
            "schema": schema,
            "table": table_id,
            "sampled_rows": result.row_count,
            "truncated": result.truncated,
        },
    )
    return _register(user_id, dataset)


def create_demo_session(user_id: str) -> dict[str, Any]:
    df = build_demo_dataframe()
    dataset = Dataset.from_records(
        df.columns.tolist(),
        df.to_dict("records"),
        name=DEMO_NAME,
        source="demo",
        source_detail={"target": DEMO_TARGET, "is_demo": True},
    )
    return _register(user_id, dataset)


def _register(user_id: str, dataset: Dataset) -> dict[str, Any]:
    session = AnalysisSession(
        id=uuid.uuid4().hex,
        user_id=user_id,
        dataset=dataset,
        cleaning=CleaningSession.start(dataset.df),
    )
    _store.add(session)
    return {"session_id": session.id, "dataset": dataset.overview()}


def list_sessions(user_id: str) -> list[dict[str, Any]]:
    out = []
    for s in _store.list_for_user(user_id):
        out.append(
            {
                "session_id": s.id,
                "name": s.dataset.name,
                "source": s.dataset.source,
                "n_rows": len(s.cleaning.current),
                "n_cols": s.cleaning.current.shape[1],
                "cleaning_steps": len(s.cleaning.history),
                "has_model": s.model_bundle is not None,
                "created_at": s.created_at,
                "last_seen": s.last_seen,
            }
        )
    return out


def get_overview(user_id: str, session_id: str) -> dict[str, Any]:
    session = _store.get(session_id, user_id)
    overview = session.working.overview()
    overview["cleaning_steps"] = len(session.cleaning.history)
    overview["has_model"] = session.model_bundle is not None
    return overview


# ------------------------------------------------------------------- analysis
def profile(user_id: str, session_id: str) -> dict[str, Any]:
    session = _store.get(session_id, user_id)
    result = profile_dataset(session.working)
    session.cache["profile"] = result
    return result


def quality(user_id: str, session_id: str, llm_context: LlmExecutionContext | None = None) -> dict[str, Any]:
    session = _store.get(session_id, user_id)
    result = analyze_quality(session.working)
    if llm_context is not None:
        result["narrative"] = insights_llm.narrate_quality(llm_context, result)
    session.cache["quality"] = result
    return result


def cleaning_recommendations(user_id: str, session_id: str) -> dict[str, Any]:
    session = _store.get(session_id, user_id)
    report = session.cache.get("quality") or analyze_quality(session.working)
    return recommend_cleaning(session.working, report)


def cleaning_preview(user_id: str, session_id: str, operations: list[dict[str, Any]]) -> dict[str, Any]:
    session = _store.get(session_id, user_id)
    _validate_ops(operations)
    return session.cleaning.preview(operations)


def cleaning_apply(
    user_id: str, session_id: str, operations: list[dict[str, Any]], llm_context: LlmExecutionContext | None = None
) -> dict[str, Any]:
    session = _store.get(session_id, user_id)
    _validate_ops(operations)
    quality_before = (session.cache.get("quality") or analyze_quality(session.working))["score"]
    step = session.cleaning.apply(operations)
    session.cache.pop("profile", None)
    session.cache.pop("eda", None)
    quality_after = analyze_quality(session.working)
    session.cache["quality"] = quality_after
    payload = {
        **step,
        "history": session.cleaning.summary(),
        "quality_before": quality_before,
        "quality_after": quality_after["score"],
    }
    if llm_context is not None:
        payload["narrative"] = insights_llm.narrate_cleaning_change(
            llm_context, quality_before, quality_after["score"], session.cleaning.summary()["steps"]
        )
    return payload


def cleaning_undo(user_id: str, session_id: str) -> dict[str, Any]:
    session = _store.get(session_id, user_id)
    ok = session.cleaning.undo()
    if not ok:
        raise BadRequestError("Nothing to undo.")
    session.cache.pop("profile", None)
    session.cache.pop("eda", None)
    session.cache["quality"] = analyze_quality(session.working)
    return {"history": session.cleaning.summary(), "quality": session.cache["quality"]["score"]}


def cleaning_reset(user_id: str, session_id: str) -> dict[str, Any]:
    session = _store.get(session_id, user_id)
    session.cleaning.reset()
    session.cache.clear()
    session.model_bundle = None
    return {"history": session.cleaning.summary()}


def eda(user_id: str, session_id: str, target: str | None = None, llm_context: LlmExecutionContext | None = None) -> dict[str, Any]:
    session = _store.get(session_id, user_id)
    if target and target not in session.cleaning.current.columns:
        raise BadRequestError(f"Column '{target}' is not in the dataset.")
    result = run_eda(session.working, target=target)
    if llm_context is not None:
        result["narrative"] = insights_llm.narrate_eda(llm_context, result)
    session.cache["eda"] = result
    return result


def ml_detect(user_id: str, session_id: str, target: str) -> dict[str, Any]:
    session = _store.get(session_id, user_id)
    try:
        return detect_task(session.working, target)
    except ValueError as exc:
        raise BadRequestError(str(exc)) from exc


def ml_train(
    user_id: str,
    session_id: str,
    *,
    target: str,
    task: str | None = None,
    models: list[str] | None = None,
    test_size: float = 0.2,
    primary_metric: str | None = None,
    cross_validation: bool = True,
    drop_columns: list[str] | None = None,
    llm_context: LlmExecutionContext | None = None,
) -> dict[str, Any]:
    session = _store.get(session_id, user_id)
    try:
        bundle = train_and_compare(
            session.working,
            target,
            task=task,
            models=models,
            test_size=test_size,
            primary_metric=primary_metric,
            cross_validation=cross_validation,
            drop_columns=drop_columns,
        )
    except ValueError as exc:
        raise BadRequestError(str(exc)) from exc
    session.model_bundle = bundle
    payload = _bundle_payload(bundle)
    if llm_context is not None:
        payload["narrative"] = insights_llm.narrate_model_results(llm_context, payload)
    return payload


def export_model(user_id: str, session_id: str) -> tuple[bytes, str]:
    """Serialise the trained pipeline + metadata as a single joblib artifact.

    We only ever *write* artifacts here; the app never loads a user-supplied
    model file (master spec §37).
    """
    import joblib

    session = _store.get(session_id, user_id)
    bundle = session.model_bundle
    if bundle is None:
        raise BadRequestError("Train a model before exporting it.")

    artifact = {
        "insightmind_artifact_version": 1,
        "pipeline": bundle.pipeline,
        "metadata": {
            "task": bundle.task,
            "target": bundle.target,
            "best_model": bundle.best_model_name,
            "primary_metric": bundle.primary_metric,
            "metrics": {k: v for k, v in bundle.metrics.items() if not isinstance(v, list)},
            "feature_columns": bundle.feature_columns,
            "feature_schema": bundle.feature_schema,
            "label_classes": bundle.label_classes,
            "n_train": bundle.n_train,
            "n_test": bundle.n_test,
            "dataset_name": session.dataset.name,
            "trained_at": time.time(),
        },
    }
    buffer = io.BytesIO()
    joblib.dump(artifact, buffer)
    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", session.dataset.name).strip("_") or "dataset"
    filename = f"insightmind_{safe_name}_{bundle.best_model_name.replace(' ', '')}.joblib"
    return buffer.getvalue(), filename


def ml_predict(user_id: str, session_id: str, feature_values: dict[str, Any]) -> dict[str, Any]:
    session = _store.get(session_id, user_id)
    if session.model_bundle is None:
        raise BadRequestError("Train a model before requesting predictions.")
    try:
        return predict_with_bundle(session.model_bundle, feature_values)
    except Exception as exc:  # noqa: BLE001
        raise BadRequestError(f"Prediction failed: {exc}") from exc


def report(user_id: str, session_id: str, llm_context: LlmExecutionContext | None = None) -> dict[str, Any]:
    session = _store.get(session_id, user_id)
    working = session.working
    profile_data = session.cache.get("profile") or profile_dataset(working)
    quality_data = session.cache.get("quality") or analyze_quality(working)
    eda_data = session.cache.get("eda")
    cleaning_data = session.cleaning.summary()
    ml_data = _bundle_payload(session.model_bundle) if session.model_bundle else None

    narrative = None
    if llm_context is not None and eda_data:
        narrative = insights_llm.narrate_eda(llm_context, eda_data)

    return build_report(
        dataset_overview=working.overview(),
        profile=profile_data,
        quality=quality_data,
        cleaning=cleaning_data,
        eda=eda_data,
        ml=ml_data,
        narrative=narrative,
    )


def ask(user_id: str, session_id: str, question: str, llm_context: LlmExecutionContext) -> dict[str, Any]:
    session = _store.get(session_id, user_id)
    working = session.working
    artifacts = {
        "dataset_overview": working.overview(),
        "data_quality": session.cache.get("quality") or analyze_quality(working),
        "cleaning_history": session.cleaning.summary()["steps"],
        "eda": _trim_eda(session.cache.get("eda")),
        "model_results": _bundle_payload(session.model_bundle) if session.model_bundle else None,
    }
    return insights_llm.answer_question(llm_context, question, artifacts)


# ------------------------------------------------------------------- helpers
def _validate_ops(operations: list[dict[str, Any]]) -> None:
    from app.data_science.cleaning import CLEANING_OPERATIONS

    if not operations:
        raise BadRequestError("No cleaning operations supplied.")
    for op in operations:
        if op.get("op") not in CLEANING_OPERATIONS:
            raise BadRequestError(f"Unknown cleaning operation: {op.get('op')!r}")


def _bundle_payload(bundle: TrainedModelBundle | None) -> dict[str, Any] | None:
    if bundle is None:
        return None
    return {
        "task": bundle.task,
        "target": bundle.target,
        "primary_metric": bundle.primary_metric,
        "best_model_name": bundle.best_model_name,
        "comparison": bundle.comparison,
        "metrics": bundle.metrics,
        "feature_importance": bundle.feature_importance,
        "feature_schema": bundle.feature_schema,
        "label_classes": bundle.label_classes,
        "n_train": bundle.n_train,
        "n_test": bundle.n_test,
        "warnings": bundle.warnings,
    }


def _trim_eda(eda_data: dict[str, Any] | None) -> dict[str, Any] | None:
    if not eda_data:
        return None
    return {
        "insights": eda_data.get("insights"),
        "numeric_summary": eda_data.get("numeric_summary"),
        "categorical_summary": eda_data.get("categorical_summary"),
        "top_correlations": (eda_data.get("correlations") or {}).get("top_pairs"),
    }


__all__ = [
    "create_session_from_records",
    "create_session_from_text",
    "create_session_from_table",
    "create_demo_session",
    "list_sessions",
    "get_overview",
    "profile",
    "quality",
    "cleaning_recommendations",
    "cleaning_preview",
    "cleaning_apply",
    "cleaning_undo",
    "cleaning_reset",
    "eda",
    "ml_detect",
    "ml_train",
    "ml_predict",
    "export_model",
    "report",
    "ask",
]
