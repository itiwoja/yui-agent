"""会話レイテンシ設定の検証。"""
import pytest

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


def test_append_chat_history_writes_user_then_model_in_one_batch(monkeypatch):
    class FakeMessages:
        def __init__(self):
            self.references = []

        def document(self):
            reference = object()
            self.references.append(reference)
            return reference

    class FakeBatch:
        def __init__(self):
            self.sets = []
            self.commit_calls = 0

        def set(self, reference, data):
            self.sets.append((reference, data))

        def commit(self):
            self.commit_calls += 1

    class FakeDb:
        def __init__(self):
            self.batch_instance = FakeBatch()

        def batch(self):
            return self.batch_instance

    messages = FakeMessages()
    db = FakeDb()
    monkeypatch.setattr(chat, "_history_ref", lambda _session_id: messages)
    monkeypatch.setattr(chat, "_db", lambda: db)

    chat.append_chat_history("session", "hello", "hi there")

    batch = db.batch_instance
    assert batch.commit_calls == 1
    assert [data["role"] for _, data in batch.sets] == ["user", "model"]
    assert [data["text"] for _, data in batch.sets] == ["hello", "hi there"]
    assert batch.sets[0][1]["created_at"] < batch.sets[1][1]["created_at"]


def test_chat_turn_uses_open_tasks_fetcher_for_known_titles(monkeypatch):
    captured = {}

    class FakeModels:
        def generate_content(self, **kwargs):
            captured.update(kwargs)
            return type(
                "Response",
                (),
                {
                    "text": (
                        '{"reply":"done","tasks":[],"completed_task_titles":[]}'
                    )
                },
            )()

    class FakeClient:
        models = FakeModels()

    open_tasks = [{"id": "task-1", "title": "Submit report"}]
    monkeypatch.setattr(chat, "get_history", lambda _session_id: [])
    monkeypatch.setattr(chat, "get_today_events", lambda: [])
    monkeypatch.setattr(chat, "_client", lambda: FakeClient())
    monkeypatch.setattr(chat, "call_with_retry", lambda operation: operation())

    result, returned_open_tasks = chat.chat_turn(
        "session",
        "I completed it",
        open_tasks_fetcher=lambda: open_tasks,
        pending_questions_fetcher=lambda: [],
    )

    assert result.reply == "done"
    assert returned_open_tasks == open_tasks
    assert "Submit report" in captured["contents"][-1].parts[0].text
    assert "保留中の質問:" not in captured["contents"][-1].parts[0].text
    assert (
        chat.PENDING_QUESTIONS_INSTRUCTION
        not in captured["config"].system_instruction
    )


def test_prefetch_context_returns_all_reply_context(monkeypatch):
    monkeypatch.setattr(
        chat, "get_history", lambda _session_id: [{"role": "user", "text": "hi"}]
    )
    monkeypatch.setattr(
        chat,
        "get_today_events",
        lambda: [{"summary": "Standup", "start": "09:00", "end": "09:30"}],
    )
    monkeypatch.setattr(chat, "find_open_tasks", lambda: [{"title": "Submit report"}])
    monkeypatch.setattr(chat, "find_pending_questions", lambda: [])

    context = chat.prefetch_context("session")

    assert context == {
        "history": [{"role": "user", "text": "hi"}],
        "today_events": [{"summary": "Standup", "start": "09:00", "end": "09:30"}],
        "open_tasks": [{"title": "Submit report"}],
        "pending_questions": [],
    }


def test_stream_reply_uses_supplied_context_without_refetching(monkeypatch):
    captured = {}

    class FakeModels:
        def generate_content_stream(self, **kwargs):
            captured.update(kwargs)
            return [type("Chunk", (), {"text": "done"})()]

    class FakeClient:
        models = FakeModels()

    monkeypatch.setattr(chat, "_client", lambda: FakeClient())
    monkeypatch.setattr(chat, "prefetch_context", lambda _session_id: pytest.fail("refetched context"))

    result = list(
        chat.stream_reply(
            "session",
            "hello",
            {
                "history": [],
                "today_events": [],
                "open_tasks": [{"title": "Submit report"}],
            },
        )
    )

    assert result == ["done"]
    assert "Submit report" in captured["contents"][-1].parts[0].text


def test_stream_reply_includes_pending_questions_in_context(monkeypatch):
    captured = {}

    class FakeModels:
        def generate_content_stream(self, **kwargs):
            captured.update(kwargs)
            return [type("Chunk", (), {"text": "done"})()]

    class FakeClient:
        models = FakeModels()

    monkeypatch.setattr(chat, "_client", lambda: FakeClient())

    list(
        chat.stream_reply(
            "session",
            "The reviewer is Maya.",
            {
                "history": [],
                "today_events": [],
                "open_tasks": [],
                "pending_questions": [
                    {
                        "id": "task-1",
                        "title": "Submit report",
                        "pending_question": "Who is the reviewer?",
                    }
                ],
            },
        )
    )

    prompt = captured["contents"][-1].parts[0].text
    assert "Submit report: Who is the reviewer?" in prompt
