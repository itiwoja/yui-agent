from agent_verify import plan_after_verification


def test_sufficient_result_progresses():
    plan = plan_after_verification("調査結果", True, "", "", [])

    assert plan["outcome"] == "progressed"
    assert plan["update"]["status"] == "in_progress"
    assert plan["update"]["agent_notes"] == "調査結果"
    assert plan["question"] is None


def test_new_followup_question_is_asked():
    plan = plan_after_verification("不足", False, "ask", "締切はいつですか？", [])

    assert plan["outcome"] == "asked"
    assert plan["update"]["status"] == "needs_input"
    assert plan["update"]["asked_questions"] == ["締切はいつですか？"]
    assert plan["question"] == "締切はいつですか？"


def test_duplicate_followup_question_is_monitored():
    plan = plan_after_verification(
        "不足", False, "ask", " 締切はいつですか？ ", ["締切はいつですか？"]
    )

    assert plan["outcome"] == "monitor"
    assert plan["update"] == {"status": "open", "agent_notes": "不足"}


def test_monitor_action_stays_open():
    plan = plan_after_verification("様子見", False, "monitor", "", [])

    assert plan["outcome"] == "monitor"
    assert plan["update"] == {"status": "open", "agent_notes": "様子見"}
