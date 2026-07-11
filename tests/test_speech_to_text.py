"""Speech-to-Text のリージョン設定に関する回帰テスト。"""
import pytest

pytest.importorskip("google.cloud.speech_v2")
speech_to_text = pytest.importorskip("speech_to_text")


def test_default_location_is_not_global():
    # chirp_2 は global に存在しないため、global を既定値に戻さない。
    assert speech_to_text.LOCATION != "global"


def test_client_uses_region_endpoint(monkeypatch):
    captured = {}

    def fake_speech_client(*, client_options):
        captured["client_options"] = client_options
        return object()

    monkeypatch.setattr(speech_to_text.speech_v2, "SpeechClient", fake_speech_client)
    monkeypatch.setattr(speech_to_text, "_client", None)

    speech_to_text._get_client()

    assert captured["client_options"].api_endpoint == (
        f"{speech_to_text.LOCATION}-speech.googleapis.com"
    )


def test_global_location_uses_default_endpoint(monkeypatch):
    captured = {}

    def fake_speech_client(*, client_options):
        captured["client_options"] = client_options
        return object()

    monkeypatch.setattr(speech_to_text, "LOCATION", "global")
    monkeypatch.setattr(speech_to_text.speech_v2, "SpeechClient", fake_speech_client)
    monkeypatch.setattr(speech_to_text, "_client", None)

    speech_to_text._get_client()

    assert captured["client_options"] is None
