from fastapi import FastAPI

import tracing


def test_setup_tracing_is_disabled_without_cloud_run_or_opt_in(monkeypatch):
    monkeypatch.delenv("K_SERVICE", raising=False)
    monkeypatch.delenv("YUI_TRACE", raising=False)
    monkeypatch.setattr(tracing, "_TRACING_ENABLED", False)

    app = FastAPI()

    assert tracing.setup_tracing(app) is False
    assert not hasattr(app.state, "yui_tracing_enabled")


def test_span_is_a_noop_when_tracing_is_disabled(monkeypatch):
    monkeypatch.setattr(tracing, "_TRACING_ENABLED", False)

    with tracing.span("test") as active_span:
        assert active_span is None
