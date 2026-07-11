"""自律ループが1件の失敗で停止しないことを確認する。"""
from datetime import datetime, timedelta, timezone

import agent_loop
import autonomous_review


class FakeReference:
    """更新内容を記録する Firestore ドキュメント参照の代替。"""

    def __init__(self):
        self.updates = []

    def update(self, value):
        self.updates.append(value)


class FakeDoc:
    """Firestore ドキュメントの最小限の代替。"""

    def __init__(self, doc_id, value=None, error=None):
        self.id = doc_id
        self.value = value
        self.error = error
        self.reference = FakeReference()

    def to_dict(self):
        if self.error:
            raise self.error
        return self.value


class FakeQuery:
    """where/limit/get の連結を再現するクエリ。"""

    def __init__(self, docs):
        self.docs = docs
        self.limit_value = None

    def where(self, *_args):
        return self

    def limit(self, value):
        self.limit_value = value
        return self

    def get(self):
        return self.docs


class FakeDb:
    """単一コレクションを返す Firestore クライアントの代替。"""

    def __init__(self, query):
        self.query = query

    def collection(self, _name):
        return self.query


def test_autonomous_review_continues_after_item_failure(monkeypatch):
    stale = datetime.now(timezone.utc) - timedelta(hours=7)
    first = FakeDoc("failed", error=RuntimeError("database unavailable"))
    second = FakeDoc(
        "processed",
        {"title": "task", "priority": 1, "reason": "reason", "last_mentioned_at": stale},
    )
    query = FakeQuery([first, second])
    monkeypatch.setattr(autonomous_review, "_db", lambda: FakeDb(query))
    monkeypatch.setattr(autonomous_review, "upsert_task", lambda *_args: None)

    result = autonomous_review.run_autonomous_review()

    assert [item["title"] for item in result["escalated"]] == ["task"]
    assert second.reference.updates
    assert query.limit_value == autonomous_review.REVIEW_LIMIT


def test_agent_loop_continues_after_item_failure_and_applies_limit(monkeypatch):
    first = FakeDoc("failed", error=RuntimeError("database unavailable"))
    second = FakeDoc(
        "processed",
        {"title": "task", "reason": "reason", "priority": 1, "asked_questions": []},
    )
    query = FakeQuery([first, second])
    monkeypatch.setattr(agent_loop, "_db", lambda: FakeDb(query))
    monkeypatch.setattr(
        agent_loop,
        "_diagnose",
        lambda *_args: agent_loop.Diagnosis(action="ask", question="question"),
    )
    monkeypatch.setattr(agent_loop, "is_duplicate", lambda *_args: False)
    monkeypatch.setattr(agent_loop, "upsert_task", lambda *_args: None)

    result = agent_loop.run_agent_loop()

    assert [item["title"] for item in result["asked"]] == ["task"]
    assert second.reference.updates
    assert query.limit_value == agent_loop.AGENT_LOOP_LIMIT
