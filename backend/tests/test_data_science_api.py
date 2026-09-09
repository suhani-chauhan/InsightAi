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
