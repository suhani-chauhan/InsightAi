"""Data Science workspace endpoints (InsightAI).

Every route is owner-scoped through ``CurrentUserDep``; sessions operate on an
in-memory analysis copy and never mutate a connected database.
"""

from __future__ import annotations

from fastapi import APIRouter, Response

from app.api.deps import CurrentUserDep
from app.api.v1.schemas.data_science import (
    AskRequest,
    CleaningOperationsRequest,
    CreateSessionRequest,
    DetectTaskRequest,
    EdaRequest,
    FromTableRequest,
    PredictRequest,
    SessionCreatedResponse,
    TrainRequest,
    UploadDatasetRequest,
)
from app.db.models.llm import LlmExecutionContext
from app.services import data_science_service as svc

router = APIRouter(prefix="/api/data-science", tags=["Data Science"])


def _llm_ctx(user_id: str, feature: str) -> LlmExecutionContext:
    return LlmExecutionContext(owner_id=user_id, feature=feature, interaction_type="explicit")


@router.get("/sessions")
def list_sessions(current_user: CurrentUserDep):
    return {"sessions": svc.list_sessions(current_user.id)}


@router.post("/sessions", response_model=SessionCreatedResponse)
def create_session(request: CreateSessionRequest, current_user: CurrentUserDep):
    return svc.create_session_from_records(
        current_user.id,
        columns=request.columns,
        rows=request.rows,
        name=request.name,
        source=request.source,
        source_detail=request.source_detail,
    )


@router.post("/sessions/from-table", response_model=SessionCreatedResponse)
async def create_session_from_table(request: FromTableRequest, current_user: CurrentUserDep):
    return await svc.create_session_from_table(
        current_user.id,
        connection_id=request.connection_id,
        table=request.table,
        schema=request.db_schema,
        limit=request.limit,
    )


@router.post("/sessions/upload", response_model=SessionCreatedResponse)
def upload_dataset(request: UploadDatasetRequest, current_user: CurrentUserDep):
    return svc.create_session_from_text(
        current_user.id,
        name=request.name,
        content=request.content,
        fmt=request.format,
        delimiter=request.delimiter,
    )


@router.post("/sessions/demo", response_model=SessionCreatedResponse)
def create_demo_session(current_user: CurrentUserDep):
    return svc.create_demo_session(current_user.id)


@router.get("/sessions/{session_id}")
def get_session(session_id: str, current_user: CurrentUserDep):
    return svc.get_overview(current_user.id, session_id)


@router.post("/sessions/{session_id}/profile")
def profile_session(session_id: str, current_user: CurrentUserDep):
    return svc.profile(current_user.id, session_id)


@router.post("/sessions/{session_id}/quality")
def quality_session(session_id: str, current_user: CurrentUserDep):
    return svc.quality(current_user.id, session_id, _llm_ctx(current_user.id, "data_science_quality"))


@router.post("/sessions/{session_id}/cleaning/recommendations")
def cleaning_recommendations(session_id: str, current_user: CurrentUserDep):
    return svc.cleaning_recommendations(current_user.id, session_id)


@router.post("/sessions/{session_id}/cleaning/preview")
def cleaning_preview(session_id: str, request: CleaningOperationsRequest, current_user: CurrentUserDep):
    return svc.cleaning_preview(current_user.id, session_id, request.as_dicts())


@router.post("/sessions/{session_id}/cleaning/apply")
def cleaning_apply(session_id: str, request: CleaningOperationsRequest, current_user: CurrentUserDep):
    return svc.cleaning_apply(
        current_user.id, session_id, request.as_dicts(), _llm_ctx(current_user.id, "data_science_cleaning")
    )


@router.post("/sessions/{session_id}/cleaning/undo")
def cleaning_undo(session_id: str, current_user: CurrentUserDep):
    return svc.cleaning_undo(current_user.id, session_id)


@router.post("/sessions/{session_id}/cleaning/reset")
def cleaning_reset(session_id: str, current_user: CurrentUserDep):
    return svc.cleaning_reset(current_user.id, session_id)


@router.post("/sessions/{session_id}/eda")
def eda_session(session_id: str, request: EdaRequest, current_user: CurrentUserDep):
    return svc.eda(current_user.id, session_id, request.target, _llm_ctx(current_user.id, "data_science_eda"))


@router.post("/sessions/{session_id}/ml/detect-task")
def detect_task(session_id: str, request: DetectTaskRequest, current_user: CurrentUserDep):
    return svc.ml_detect(current_user.id, session_id, request.target)


@router.post("/sessions/{session_id}/ml/train")
def train_models(session_id: str, request: TrainRequest, current_user: CurrentUserDep):
    return svc.ml_train(
        current_user.id,
        session_id,
        target=request.target,
        task=request.task,
        models=request.models,
        test_size=request.test_size,
        primary_metric=request.primary_metric,
        cross_validation=request.cross_validation,
        drop_columns=request.drop_columns,
        llm_context=_llm_ctx(current_user.id, "data_science_ml"),
    )


@router.post("/sessions/{session_id}/ml/predict")
def predict(session_id: str, request: PredictRequest, current_user: CurrentUserDep):
    return svc.ml_predict(current_user.id, session_id, request.feature_values)


@router.get("/sessions/{session_id}/ml/model")
def download_model(session_id: str, current_user: CurrentUserDep):
    data, filename = svc.export_model(current_user.id, session_id)
    return Response(
        content=data,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/sessions/{session_id}/report")
def generate_report(session_id: str, current_user: CurrentUserDep):
    return svc.report(current_user.id, session_id, _llm_ctx(current_user.id, "data_science_report"))


@router.post("/sessions/{session_id}/ask")
def ask_insightai(session_id: str, request: AskRequest, current_user: CurrentUserDep):
    return svc.ask(current_user.id, session_id, request.question, _llm_ctx(current_user.id, "data_science_ask"))


@router.post("/sessions/{session_id}/query")
def query_dataset(session_id: str, request: AskRequest, current_user: CurrentUserDep):
    """Natural-language data query — LLM writes read-only DuckDB SQL over the dataset."""
    return svc.nl_query(current_user.id, session_id, request.question, _llm_ctx(current_user.id, "data_science_query"))
