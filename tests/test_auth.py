"""auth.py — トークン検証の純ロジックテスト。"""
import pytest

from auth import assert_token_configured, is_authorized


def test_cloud_run_requires_a_configured_token(monkeypatch):
    monkeypatch.setenv("K_SERVICE", "yui")
    monkeypatch.delenv("YUI_APP_TOKEN", raising=False)

    with pytest.raises(RuntimeError, match="YUI_APP_TOKEN"):
        assert_token_configured()


def test_cloud_run_accepts_a_configured_token(monkeypatch):
    monkeypatch.setenv("K_SERVICE", "yui")
    monkeypatch.setenv("YUI_APP_TOKEN", "configured-token")

    assert_token_configured()


def test_local_development_allows_no_token(monkeypatch):
    monkeypatch.delenv("K_SERVICE", raising=False)
    monkeypatch.delenv("YUI_APP_TOKEN", raising=False)

    assert_token_configured()


def test_open_when_no_token_configured():
    # 開発時: YUI_APP_TOKEN 未設定なら素通し（従来挙動を壊さない）
    assert is_authorized("", "anything") is True
    assert is_authorized("", "") is True
    assert is_authorized("   ", "x") is True  # 空白のみも未設定扱い


def test_requires_match_when_configured():
    assert is_authorized("s3cret", "s3cret") is True
    assert is_authorized("s3cret", "wrong") is False


def test_missing_token_is_rejected_when_configured():
    assert is_authorized("s3cret", "") is False
    assert is_authorized("s3cret", "   ") is False


def test_whitespace_is_trimmed_both_sides():
    assert is_authorized("s3cret", "  s3cret  ") is True


def test_bom_prefix_is_ignored():
    # WindowsのSecret Manager経由で先頭にBOMが混入しても正しく突合する
    assert is_authorized("﻿s3cret", "s3cret") is True
    assert is_authorized("s3cret", "﻿s3cret") is True
