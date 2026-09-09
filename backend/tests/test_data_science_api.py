"""Data Science workspace API — routing, auth scoping, end-to-end flow (master spec §53)."""

import os

os.environ.setdefault("ENCRYPTION_KEY", "TZZoA4e_0aRy3zO0u7FzjHwBq2L8y6b9R9oV8XmQ_Jw=")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "service-role-key")
os.environ.setdefault("SUPABASE_JWT_SECRET", "jwt-secret")
os.environ.setdefault("GROQ_API_KEY", "groq-test-key")
os.environ.setdefault("LEMON_SQUEEZY_WEBHOOK_SECRET", "webhook-secret")

import pytest
from fastapi.testclient import TestClient

from app.integrations.supabase_auth import get_current_user
from app.integrations.supabase_auth.dependencies import User
from app.main import app

USER_A = User(id="ds-user-a", email="a@example.com")
USER_B = User(id="ds-user-b", email="b@example.com")


@pytest.fixture
def client_as_a():
    # Preserve any override another test module installed at import time.
    previous = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = lambda: USER_A
    yield TestClient(app)
    if previous is not None:
        app.dependency_overrides[get_current_user] = previous
    else:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def demo_session(client_as_a):
    resp = client_as_a.post("/api/data-science/sessions/demo")
    assert resp.status_code == 200, resp.text
    return resp.json()["session_id"]


def test_create_session_from_records(client_as_a):
    payload = {
        "columns": ["a", "b"],
        "rows": [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}, {"a": 3, "b": "x"}],
        "name": "test result",
    }
    resp = client_as_a.post("/api/data-science/sessions", json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["session_id"]
    assert body["dataset"]["n_rows"] == 3
    assert body["dataset"]["n_cols"] == 2


def test_empty_rows_rejected(client_as_a):
    resp = client_as_a.post("/api/data-science/sessions", json={"columns": ["a"], "rows": []})
    assert resp.status_code == 422  # schema min_length


def test_upload_csv_creates_session(client_as_a):
    csv = "name,age,city\nAda,36,London\nAlan,41,Manchester\nGrace,45,New York\n"
    resp = client_as_a.post(
        "/api/data-science/sessions/upload",
        json={"name": "people.csv", "content": csv, "format": "csv"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["dataset"]["n_rows"] == 3
    assert body["dataset"]["n_cols"] == 3
    assert body["dataset"]["source"] == "upload"


def test_upload_tsv_supported(client_as_a):
    tsv = "a\tb\n1\t2\n3\t4\n"
    resp = client_as_a.post(
        "/api/data-science/sessions/upload",
        json={"name": "t.tsv", "content": tsv, "format": "tsv"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["dataset"]["n_cols"] == 2


def test_upload_autodetects_semicolon_delimiter(client_as_a):
    # The python parser sniffs the delimiter when none is given.
    weird = "a;b;c\n1;2;3\n4;5;6\n"
    resp = client_as_a.post(
        "/api/data-science/sessions/upload",
        json={"name": "semi.csv", "content": weird, "format": "csv"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["dataset"]["n_cols"] == 3


def test_upload_wrong_delimiter_in_header_is_rejected(client_as_a):
    # Header kept its separators because the parser couldn't split -> flag it.
    bad = "a|b|c\nx|y|z\n"
    resp = client_as_a.post(
        "/api/data-science/sessions/upload",
        json={"name": "pipe.csv", "content": bad, "format": "csv", "delimiter": ","},
    )
    assert resp.status_code == 400
    assert "delimiter" in resp.json()["error"]["message"].lower()


def test_upload_legit_single_column_is_accepted(client_as_a):
    single = "value\nalpha\nbravo\ncharlie\n"
    resp = client_as_a.post(
        "/api/data-science/sessions/upload",
        json={"name": "list.csv", "content": single, "format": "csv"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["dataset"]["n_cols"] == 1


def test_upload_header_only_rejected(client_as_a):
    resp = client_as_a.post(
        "/api/data-science/sessions/upload",
        json={"name": "empty.csv", "content": "a,b,c\n", "format": "csv"},
    )
    assert resp.status_code == 400


def test_from_table_creates_session(client_as_a, monkeypatch):
    from app.query_engine.results import QueryExecutionResult
    from app.services import query_execution_service

    async def fake_exec(user_id, connection_id, sql, row_limit=500, readonly=None):
        assert sql == 'SELECT * FROM "public"."customers" LIMIT 100'
        return QueryExecutionResult(
            success=True,
            columns=["id", "country"],
            rows=[{"id": 1, "country": "US"}, {"id": 2, "country": "UK"}],
            row_count=2,
        )

    monkeypatch.setattr(query_execution_service, "execute_for_connection", fake_exec)
    resp = client_as_a.post(
        "/api/data-science/sessions/from-table",
        json={"connection_id": "c1", "table": "customers", "db_schema": "public", "limit": 100},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["dataset"]["source"] == "database_table"
    assert body["dataset"]["n_rows"] == 2


def test_from_table_rejects_unsafe_identifier(client_as_a, monkeypatch):
    from app.services import query_execution_service

    called = False

    async def fake_exec(*a, **k):
        nonlocal called
        called = True
        raise AssertionError("executor must not run for an invalid identifier")

    monkeypatch.setattr(query_execution_service, "execute_for_connection", fake_exec)
    resp = client_as_a.post(
        "/api/data-science/sessions/from-table",
        json={"connection_id": "c1", "table": "users; DROP TABLE users"},
    )
    assert resp.status_code in (400, 422)
    assert called is False


def test_from_table_surfaces_execution_error(client_as_a, monkeypatch):
    from app.query_engine.results import QueryExecutionResult
    from app.services import query_execution_service

    async def fake_exec(*a, **k):
        return QueryExecutionResult(success=False, error="permission denied for table secrets")

    monkeypatch.setattr(query_execution_service, "execute_for_connection", fake_exec)
    resp = client_as_a.post(
        "/api/data-science/sessions/from-table",
        json={"connection_id": "c1", "table": "secrets"},
    )
    assert resp.status_code == 400
    assert "permission denied" in resp.json()["error"]["message"]


def test_profile_quality_flow(client_as_a, demo_session):
    prof = client_as_a.post(f"/api/data-science/sessions/{demo_session}/profile")
    assert prof.status_code == 200
    assert prof.json()["dataset"]["n_rows"] > 0

    qual = client_as_a.post(f"/api/data-science/sessions/{demo_session}/quality")
    assert qual.status_code == 200
    q = qual.json()
    assert 0 <= q["score"]["overall"] <= 100
    assert q["issue_count"] >= 1


def test_cleaning_recommend_preview_apply_undo(client_as_a, demo_session):
    recs = client_as_a.post(f"/api/data-science/sessions/{demo_session}/cleaning/recommendations").json()
    assert recs["recommendations"]
    ops = [r["operation"] for r in recs["recommendations"] if r["risk"] == "low"][:3]
    assert ops

    preview = client_as_a.post(
        f"/api/data-science/sessions/{demo_session}/cleaning/preview", json={"operations": ops}
    ).json()
    assert "before" in preview and "after" in preview

    applied = client_as_a.post(
        f"/api/data-science/sessions/{demo_session}/cleaning/apply", json={"operations": ops}
    ).json()
    assert "quality_before" in applied and "quality_after" in applied

    undo = client_as_a.post(f"/api/data-science/sessions/{demo_session}/cleaning/undo")
    assert undo.status_code == 200


def test_eda_and_ml_end_to_end(client_as_a, demo_session):
    eda = client_as_a.post(
        f"/api/data-science/sessions/{demo_session}/eda", json={"target": "Attrition"}
    )
    assert eda.status_code == 200
    assert eda.json()["charts"]

    detect = client_as_a.post(
        f"/api/data-science/sessions/{demo_session}/ml/detect-task", json={"target": "Attrition"}
    ).json()
    assert detect["detected_task"] == "classification"

    train = client_as_a.post(
        f"/api/data-science/sessions/{demo_session}/ml/train",
        json={"target": "Attrition", "cross_validation": False},
    )
    assert train.status_code == 200, train.text
    result = train.json()
    assert result["best_model_name"]
    assert result["feature_importance"]
    assert result["comparison"]

    schema = result["feature_schema"]
    feature_values = {
        s["name"]: (s.get("median") if s["type"] == "number" else (s["options"][0] if s.get("options") else None))
        for s in schema
    }
    pred = client_as_a.post(
        f"/api/data-science/sessions/{demo_session}/ml/predict", json={"feature_values": feature_values}
    )
    assert pred.status_code == 200, pred.text
    assert "prediction" in pred.json()

    report = client_as_a.post(f"/api/data-science/sessions/{demo_session}/report")
    assert report.status_code == 200
    assert {s["id"] for s in report.json()["sections"]} >= {"overview", "quality", "ml"}


def test_download_model_returns_loadable_joblib(client_as_a, demo_session):
    import io

    import joblib
    from sklearn.pipeline import Pipeline

    train = client_as_a.post(
        f"/api/data-science/sessions/{demo_session}/ml/train",
        json={"target": "Attrition", "cross_validation": False},
    )
    assert train.status_code == 200, train.text

    resp = client_as_a.get(f"/api/data-science/sessions/{demo_session}/ml/model")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/octet-stream"
    assert ".joblib" in resp.headers["content-disposition"]

    artifact = joblib.load(io.BytesIO(resp.content))
    assert isinstance(artifact["pipeline"], Pipeline)
    assert artifact["metadata"]["target"] == "Attrition"
    assert artifact["metadata"]["feature_columns"]


def test_download_model_requires_training(client_as_a, demo_session):
    resp = client_as_a.get(f"/api/data-science/sessions/{demo_session}/ml/model")
    assert resp.status_code == 400


def test_predict_requires_trained_model(client_as_a, demo_session):
    resp = client_as_a.post(
        f"/api/data-science/sessions/{demo_session}/ml/predict", json={"feature_values": {}}
    )
    assert resp.status_code == 400


def test_sessions_are_user_scoped(client_as_a, demo_session):
    try:
        app.dependency_overrides[get_current_user] = lambda: USER_B
        other = TestClient(app)
        resp = other.get(f"/api/data-science/sessions/{demo_session}")
        assert resp.status_code == 404
    finally:
        app.dependency_overrides[get_current_user] = lambda: USER_A


def test_unknown_session_404(client_as_a):
    resp = client_as_a.post("/api/data-science/sessions/does-not-exist/profile")
    assert resp.status_code == 404
