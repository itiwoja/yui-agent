"""Firestore のタスク言及マージを検証する。"""
import pytest

pytest.importorskip("google.cloud.firestore")
memory_store = pytest.importorskip("memory_store")


class FakeDocument:
    def __init__(self, data, doc_id="task-1"):
        self.data = data
        self.id = doc_id
        self.updated = []
        self.reference = self

    def to_dict(self):
        return self.data

    def update(self, data):
        self.updated.append(data)


class FakeTaskMentions:
    def __init__(self, previous):
        self.previous = previous
        self.added = []
        self.where_calls = []
        self.limit_calls = []

    def where(self, *args):
        self.where_calls.append(args)
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def limit(self, _limit):
        self.limit_calls.append(_limit)
        return self

    def get(self):
        return self.previous

    def add(self, data):
        self.added.append(data)


class FakeFirestore:
    def __init__(self, task_mentions):
        self.task_mentions = task_mentions

    def collection(self, name):
        assert name == memory_store.COLLECTION
        return self.task_mentions


def _configure_firestore(monkeypatch, previous):
    task_mentions = FakeTaskMentions(previous)
    monkeypatch.setattr(memory_store, "_client", lambda: FakeFirestore(task_mentions))
    return task_mentions


def test_record_and_resolve_creates_first_mention(monkeypatch):
    task_mentions = _configure_firestore(monkeypatch, [])

    result = memory_store.record_and_resolve("請求書を確認", 3, "月末まで")

    assert result == {
        "title": "請求書を確認",
        "priority": 3,
        "reason": "月末まで",
        "mention_count": 1,
        "promoted": False,
        "previous_priority": 3,
    }
    assert task_mentions.added[0]["mention_count"] == 1
    assert task_mentions.added[0]["priority"] == 3


def test_record_and_resolve_keeps_promoted_priority_for_lower_remention(monkeypatch):
    previous = FakeDocument({"priority": 4, "mention_count": 2})
    _configure_firestore(monkeypatch, [previous])

    result = memory_store.record_and_resolve("請求書を確認", 2, "月末まで")

    assert result["priority"] == 5
    assert result["mention_count"] == 3
    assert result["promoted"] is True
    assert previous.updated[0]["priority"] == 5


def test_record_and_resolve_uses_higher_incoming_priority(monkeypatch):
    previous = FakeDocument({"priority": 2, "mention_count": 4})
    _configure_firestore(monkeypatch, [previous])

    result = memory_store.record_and_resolve("請求書を確認", 5, "今日中")

    assert result["priority"] == 5
    assert result["mention_count"] == 5
    assert result["promoted"] is False
    assert previous.updated[0]["priority"] == 5


def test_find_pending_questions_filters_and_limits_results(monkeypatch):
    pending = [
        FakeDocument(
            {"title": "Submit report", "pending_question": "Who is the reviewer?"}
        )
    ]
    task_mentions = _configure_firestore(monkeypatch, pending)

    assert memory_store.find_pending_questions(limit=2) == [
        {
            "id": "task-1",
            "title": "Submit report",
            "pending_question": "Who is the reviewer?",
        }
    ]
    assert task_mentions.where_calls == [("status", "==", "needs_input")]
    assert task_mentions.limit_calls == [2]
