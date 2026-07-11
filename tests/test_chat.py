"""会話レイテンシ設定の検証。"""
import chat


def test_thinking_budget_uses_default_and_environment_override(monkeypatch):
    monkeypatch.delenv("YUI_THINKING_BUDGET", raising=False)
    assert chat._thinking_budget() == 512

    monkeypatch.setenv("YUI_THINKING_BUDGET", "256")
    assert chat._thinking_budget() == 256


def test_thinking_budget_normalizes_negative_and_invalid_values(monkeypatch):
    monkeypatch.setenv("YUI_THINKING_BUDGET", "-4")
    assert chat._thinking_budget() == -1

    monkeypatch.setenv("YUI_THINKING_BUDGET", "invalid")
    assert chat._thinking_budget() == 512


def test_history_limit_uses_default_and_valid_environment_override(monkeypatch):
    monkeypatch.delenv("YUI_HISTORY_LIMIT", raising=False)
    assert chat._history_limit() == 12

    monkeypatch.setenv("YUI_HISTORY_LIMIT", "0")
    assert chat._history_limit() == 0

    monkeypatch.setenv("YUI_HISTORY_LIMIT", "8")
    assert chat._history_limit() == 8


def test_history_limit_falls_back_for_negative_or_invalid_values(monkeypatch):
    monkeypatch.setenv("YUI_HISTORY_LIMIT", "-1")
    assert chat._history_limit() == 12

    monkeypatch.setenv("YUI_HISTORY_LIMIT", "invalid")
    assert chat._history_limit() == 12
