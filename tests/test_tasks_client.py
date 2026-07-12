"""Google Tasks の検索・登録ヘルパーを検証する。"""
import pytest

pytest.importorskip("googleapiclient")
tasks_client = pytest.importorskip("tasks_client")
_find_matching_task = tasks_client._find_matching_task


def test_upsert_task_reuses_the_task_list_cache_within_ttl(monkeypatch):
    service = FakeUpsertService([])
    tasks_client._task_cache.clear()
    monkeypatch.setenv("YUI_TASKS_CACHE_TTL", "60")
    _configure_upsert(monkeypatch, service)

    tasks_client.upsert_task("Repeated task", 3, "first")
    tasks_client.upsert_task("Repeated task", 3, "updated")

    assert service.fake_tasks.list_calls == [
        {"tasklist": "list-1", "showCompleted": False}
    ]
    assert len(service.fake_tasks.insert_calls) == 1
    assert len(service.fake_tasks.patch_calls) == 1


class FakeTasks:
    def __init__(self, items):
        self.items = items
        self.list_calls = []

    def list(self, **kwargs):
        self.list_calls.append(kwargs)
        return self

    def execute(self):
        return {"items": self.items}


class FakeService:
    def __init__(self, items):
        self.fake_tasks = FakeTasks(items)

    def tasks(self):
        return self.fake_tasks


def test_find_matching_task_uses_titles_match_and_lists_once():
    service = FakeService([{"id": "task-1", "title": "🟡 会議資料作成"}])

    result = _find_matching_task(service, "list-1", "会議資料作成")

    assert result == {"id": "task-1", "title": "🟡 会議資料作成"}
    assert service.fake_tasks.list_calls == [
        {"tasklist": "list-1", "showCompleted": False}
    ]


def test_find_matching_task_returns_none_when_no_title_matches():
    service = FakeService([{"id": "task-1", "title": "別のタスク"}])

    assert _find_matching_task(service, "list-1", "会議資料作成") is None


def test_find_matching_task_refreshes_a_stale_cache_once_when_it_misses():
    service = FakeService([])
    tasks_client._task_cache.clear()

    assert _find_matching_task(service, "list-1", "Fresh task") is None
    service.fake_tasks.items.append({"id": "task-2", "title": "Fresh task"})

    assert _find_matching_task(service, "list-1", "Fresh task") == {
        "id": "task-2",
        "title": "Fresh task",
    }
    assert service.fake_tasks.list_calls == [
        {"tasklist": "list-1", "showCompleted": False},
        {"tasklist": "list-1", "showCompleted": False},
    ]


class FakeMutation:
    def __init__(self, response):
        self.response = response

    def execute(self):
        return self.response


class FakeUpsertTasks(FakeTasks):
    def __init__(self, items):
        super().__init__(items)
        self.patch_calls = []
        self.insert_calls = []

    def patch(self, **kwargs):
        self.patch_calls.append(kwargs)
        return FakeMutation({"id": "updated-task"})

    def insert(self, **kwargs):
        self.insert_calls.append(kwargs)
        return FakeMutation({"id": "created-task"})


class FakeUpsertService:
    def __init__(self, items):
        self.fake_tasks = FakeUpsertTasks(items)

    def tasks(self):
        return self.fake_tasks


def _configure_upsert(monkeypatch, service):
    monkeypatch.setattr(tasks_client, "_service", lambda: service)
    monkeypatch.setattr(
        tasks_client, "_get_or_create_tasklist_id", lambda _service: "list-1"
    )


def test_complete_google_task_refreshes_a_missed_fresh_cache(monkeypatch):
    service = FakeUpsertService([])
    tasks_client._task_cache.clear()
    _configure_upsert(monkeypatch, service)

    tasks_client._cached_tasks(service, "list-1")
    service.fake_tasks.items.append({"id": "task-1", "title": "Fresh task"})

    assert tasks_client.complete_google_task("Fresh task") == "updated-task"
    assert service.fake_tasks.list_calls == [
        {"tasklist": "list-1", "showCompleted": False},
        {"tasklist": "list-1", "showCompleted": False},
    ]
    assert service.fake_tasks.patch_calls[-1]["body"] == {"status": "completed"}


@pytest.mark.parametrize("operation", ["complete", "delete"])
def test_google_task_mutations_warn_when_a_task_is_missing(monkeypatch, operation):
    warnings = []
    monkeypatch.setattr(tasks_client, "_service", lambda: object())
    monkeypatch.setattr(
        tasks_client, "_get_or_create_tasklist_id", lambda _service: "list-1"
    )
    monkeypatch.setattr(tasks_client, "_find_matching_task", lambda *_args: None)
    monkeypatch.setattr(
        tasks_client.obs,
        "warning",
        lambda *args, **kwargs: warnings.append((args, kwargs)),
    )

    result = getattr(tasks_client, f"{operation}_google_task")("Missing task")

    assert result is None
    assert warnings == [
        (("google task not found",), {"op": operation, "title": "Missing task"})
    ]


def test_upsert_task_patches_matching_task_without_inserting(monkeypatch):
    service = FakeUpsertService([{"id": "task-1", "title": "会議資料作成"}])
    _configure_upsert(monkeypatch, service)

    result = tasks_client.upsert_task("会議資料作成", 3, "明日の会議用")

    assert result == "updated-task"
    assert service.fake_tasks.patch_calls == [
        {
            "tasklist": "list-1",
            "task": "task-1",
            "body": {"title": "🟡 会議資料作成", "notes": "明日の会議用"},
        }
    ]
    assert service.fake_tasks.insert_calls == []


def test_upsert_task_inserts_when_no_task_matches(monkeypatch):
    service = FakeUpsertService([])
    _configure_upsert(monkeypatch, service)

    result = tasks_client.upsert_task("会議資料作成", 3, "明日の会議用")

    assert result == "created-task"
    assert service.fake_tasks.patch_calls == []
    assert service.fake_tasks.insert_calls == [
        {
            "tasklist": "list-1",
            "body": {"title": "🟡 会議資料作成", "notes": "明日の会議用"},
        }
    ]


def test_upsert_task_marks_highest_priority_with_red_label(monkeypatch):
    service = FakeUpsertService([])
    _configure_upsert(monkeypatch, service)

    tasks_client.upsert_task("障害対応", 5, "至急")

    assert service.fake_tasks.insert_calls[0]["body"]["title"] == "🔴 障害対応"


def test_upsert_task_uses_plain_title_for_unknown_priority(monkeypatch):
    service = FakeUpsertService([])
    _configure_upsert(monkeypatch, service)

    tasks_client.upsert_task("障害対応", 99, "優先度不明")

    assert service.fake_tasks.insert_calls[0]["body"]["title"] == "障害対応"
