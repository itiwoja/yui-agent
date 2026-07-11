"""エージェントの自己検証後の状態遷移を決める純ロジック。"""

from dedup import is_duplicate


def plan_after_verification(
    note: str,
    sufficient: bool,
    followup_action: str,
    question: str,
    asked_questions: list[str],
) -> dict:
    """自己検証の結果からFirestore更新内容と分類を返す。"""
    if sufficient:
        return {
            "outcome": "progressed",
            "update": {
                "status": "in_progress",
                "agent_notes": note,
                "pending_question": None,
            },
            "question": None,
        }

    question = question.strip()
    if (
        followup_action == "ask"
        and question
        and not is_duplicate(question, asked_questions)
    ):
        return {
            "outcome": "asked",
            "update": {
                "status": "needs_input",
                "pending_question": question,
                "asked_questions": [*asked_questions, question],
            },
            "question": question,
        }

    return {
        "outcome": "monitor",
        "update": {"status": "open", "agent_notes": note},
        "question": None,
    }
