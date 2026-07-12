"""セキュリティ上限を HTTP レイヤーで検証する。"""
import os

import pytest

import rate_limit

os.environ["YUI_APP_TOKEN"] = "test-token"

pytest.importorskip("httpx")
try:
    from fastapi.testclient import TestClient

    from main import app
except Exception as exc:
    pytest.skip(f"main import unavailable: {exc}", allow_module_level=True)

client = TestClient(app)
HEADERS = {"X-Yui-Token": "test-token"}


def test_request_body_limits_are_enforced():
    response = client.post("/process", json={"text": "x" * 4001}, headers=HEADERS)
    assert response.status_code == 422
    assert (
        client.post(
            "/chat",
            json={"session_id": "s" * 129, "message": "hello"},
            headers=HEADERS,
        ).status_code
        == 422
    )
    response = client.post(
        "/chat",
        json={"session_id": "session", "message": "x" * 4001},
        headers=HEADERS,
    )
    assert response.status_code == 422
    response = client.post("/tts", json={"text": "x" * 1001}, headers=HEADERS)
    assert response.status_code == 422
    assert (
        client.post(
            "/tasks/task/answer",
            json={"answer": "x" * 2001},
            headers=HEADERS,
        ).status_code
        == 422
    )


def test_transcribe_rejects_payload_larger_than_ten_megabytes():
    resp = client.post(
        "/transcribe",
        content=b"x" * (10 * 1024 * 1024 + 1),
        headers={**HEADERS, "Content-Type": "audio/wav"},
    )
    assert resp.status_code == 413


def test_audio_endpoints_reject_non_audio_content_types():
    rate_limit.clear_rate_limits()

    transcribe = client.post(
        "/transcribe",
        content=b"not audio",
        headers={**HEADERS, "Content-Type": "text/plain"},
    )
    converse = client.post(
        "/converse",
        content=b"not audio",
        headers={**HEADERS, "Content-Type": "text/plain"},
    )

    assert transcribe.status_code == 415
    assert converse.status_code == 415


def test_security_headers_are_added_to_responses():
    response = client.get("/health")

    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
