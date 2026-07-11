import pytest

from retry import call_with_retry


def test_succeeds_on_third_attempt_without_real_sleep():
    calls = 0
    delays = []

    def flaky():
        nonlocal calls
        calls += 1
        if calls < 3:
            raise RuntimeError("503 unavailable")
        return "ok"

    assert call_with_retry(flaky, sleep=delays.append) == "ok"
    assert calls == 3
    assert delays == [0.5, 1.0]


def test_raises_last_exception_after_attempts():
    calls = 0

    def failing():
        nonlocal calls
        calls += 1
        raise TimeoutError("timeout")

    with pytest.raises(TimeoutError):
        call_with_retry(failing, attempts=2, sleep=lambda _: None)
    assert calls == 2


def test_non_transient_exception_is_not_retried():
    calls = 0

    def failing():
        nonlocal calls
        calls += 1
        raise ValueError("bad request")

    with pytest.raises(ValueError):
        call_with_retry(failing, sleep=lambda _: None)
    assert calls == 1


def test_custom_transient_predicate_and_sleep_are_injected():
    calls = 0
    delays = []

    def flaky():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("try again")
        return 42

    result = call_with_retry(
        flaky,
        is_transient=lambda exc: "again" in str(exc),
        sleep=delays.append,
        base_delay=0.25,
    )

    assert result == 42
    assert delays == [0.25]
