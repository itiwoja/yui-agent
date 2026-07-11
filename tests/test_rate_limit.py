"""レート制限の固定窓ロジックを検証する。"""
from rate_limit import is_allowed


def test_allows_requests_up_to_limit():
    history: list[float] = []

    assert is_allowed(history, now=1.0, limit=2, window=60.0) is True
    assert is_allowed(history, now=2.0, limit=2, window=60.0) is True


def test_rejects_request_over_limit():
    history = [1.0, 2.0]

    assert is_allowed(history, now=3.0, limit=2, window=60.0) is False


def test_allows_after_window_expires():
    history = [1.0, 2.0]

    assert is_allowed(history, now=62.0, limit=2, window=60.0) is True
    assert history == [62.0]
