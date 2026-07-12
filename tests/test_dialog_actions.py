import dialog_actions


def test_extract_dialog_actions_uses_known_titles_and_returns_parsed_result(monkeypatch):
    captured = {}

    class FakeModels:
        def generate_content(self, **kwargs):
            captured.update(kwargs)
            return type(
                "Response",
                (),
                {
                    "text": (
                        '{"tasks":[{"title":"Buy milk","priority":2,'
                        '"reason":"needed","confidence":0.9}],'
                        '"completed_task_titles":["Write report"],'
                        '"question_answers":[{"task_title":"Submit report",'
                        '"answer":"Maya is the reviewer."}]}'
                    )
                },
            )()

    class FakeClient:
        models = FakeModels()

    monkeypatch.setattr(dialog_actions, "_client", lambda: FakeClient())
    monkeypatch.setattr(dialog_actions, "call_with_retry", lambda operation: operation())

    tasks, completed, answers = dialog_actions.extract_dialog_actions(
        "I finished the report and need milk",
        ["Write report"],
        [
            {
                "title": "Submit report",
                "pending_question": "Who is the reviewer?",
            }
        ],
    )

    assert tasks[0].title == "Buy milk"
    assert completed == ["Write report"]
    assert answers[0].task_title == "Submit report"
    assert answers[0].answer == "Maya is the reviewer."
    assert "Write report" in captured["contents"]
    assert "Who is the reviewer?" in captured["contents"]
