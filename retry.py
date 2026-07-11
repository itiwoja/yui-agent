"""外部APIの一時的な失敗を指数バックオフで再試行する。"""

import time

TRANSIENT_MARKERS = ("503", "429", "deadline", "unavailable", "timeout", "timed out")


def is_transient_error(exc: Exception) -> bool:
    """例外メッセージが代表的な一時障害を示すかを保守的に判定する。"""
    message = str(exc).lower()
    return any(marker in message for marker in TRANSIENT_MARKERS)


def call_with_retry(
    fn,
    attempts=3,
    is_transient=is_transient_error,
    sleep=time.sleep,
    base_delay=0.5,
):
    """一時例外なら指数バックオフし、最大attempts回までfnを呼ぶ。"""
    if attempts < 1:
        raise ValueError("attempts must be at least 1")

    for attempt in range(attempts):
        try:
            return fn()
        except Exception as exc:
            if not is_transient(exc) or attempt == attempts - 1:
                raise
            sleep(base_delay * (2**attempt))

    raise AssertionError("unreachable")
