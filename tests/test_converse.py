import json
import os

import pytest

os.environ["YUI_APP_TOKEN"] = "test-token"

pytest.importorskip("httpx")
try:
    from fastapi.testclient import TestClient

    import main
except Exception as exc:
    pytest.skip(f"main import unavailable: {exc}", allow_module_level=True)


HEADERS = {"X-Yui-Token": "test-token"}


def test_converse_streams_transcript_audio_and_done(monkeypatch):
    monkeypatch.setattr(main, "transcribe_audio", lambda _audio: "hello")
    monkeypatch.setattr(main, "stream_reply", lambda *_args: iter(["Hello world."]))
    monkeypatch.setattr(main, "synthesize_speech", lambda _text: b"mp3")
    monkeypatch.setattr(main, "_finalize_converse_background", lambda *_args: None)

    client = TestClient(main.app)
    response = client.post("/converse?session_id=session", content=b"audio", headers=HEADERS)
    events = [json.loads(line) for line in response.text.splitlines()]

    assert response.headers["content-type"].startswith("application/x-ndjson")
    assert [event["type"] for event in events] == ["transcript", "audio", "done"]
    assert events[1]["data"] == "bXAz"
    assert events[-1]["reply"] == "Hello world."


def test_converse_emits_empty_for_empty_transcript(monkeypatch):
    monkeypatch.setattr(main, "transcribe_audio", lambda _audio: "  ")

    client = TestClient(main.app)
    response = client.post("/converse", content=b"audio", headers=HEADERS)

    assert [json.loads(line) for line in response.text.splitlines()] == [{"type": "empty"}]
