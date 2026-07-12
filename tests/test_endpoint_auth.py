"""保護エンドポイントが実際に401を返す配線テスト（google依存が無い環境ではskip）。

auth の Depends はルート本体より前に走るので、未認証リクエストは Firestore や
Gemini に触れずに401で弾かれる（＝この検証はクレデンシャル不要）。
"""
import os

import pytest

import rate_limit

os.environ["YUI_APP_TOKEN"] = "test-token"

pytest.importorskip("httpx")
try:
    from fastapi.testclient import TestClient

    from main import app
except Exception as exc:  # google クライアント系が未インストールのローカル軽量環境
    pytest.skip(f"main import unavailable: {exc}", allow_module_level=True)

client = TestClient(app)


def test_health_is_open():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_chat_rejected_without_token():
    resp = client.post("/chat", json={"session_id": "s", "message": "やあ"})
    assert resp.status_code == 401


def test_chat_rejected_with_wrong_token():
    resp = client.post(
        "/chat",
        json={"session_id": "s", "message": "やあ"},
        headers={"X-Yui-Token": "wrong"},
    )
    assert resp.status_code == 401


def test_autonomous_review_rejected_without_token():
    resp = client.post("/autonomous-review")
    assert resp.status_code == 401


def test_tasks_accepts_valid_query_token(monkeypatch):
    monkeypatch.setattr("main.list_tasks", lambda: [])

    response = client.get("/tasks?token=test-token")

    assert response.status_code != 401


def test_tasks_accepts_valid_header_token(monkeypatch):
    monkeypatch.setattr("main.list_tasks", lambda: [])

    response = client.get("/tasks", headers={"X-Yui-Token": "test-token"})

    assert response.status_code != 401


def test_internal_finalize_turn_is_rate_limited(monkeypatch):
    rate_limit.clear_rate_limits()
    monkeypatch.setenv("YUI_RATE_LIMIT", "1")
    monkeypatch.setattr("main.finalize_turn", lambda *_args: None)

    first = client.post(
        "/internal/finalize-turn",
        json={"session_id": "session", "user_text": "hello", "reply": "reply"},
        headers={"X-Yui-Token": "test-token"},
    )
    second = client.post(
        "/internal/finalize-turn",
        json={"session_id": "session", "user_text": "hello", "reply": "reply"},
        headers={"X-Yui-Token": "test-token"},
    )

    assert first.status_code == 200
    assert second.status_code == 429
