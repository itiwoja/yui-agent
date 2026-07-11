"""Extract task changes from a completed conversational turn."""

from __future__ import annotations

from google.genai import types
from pydantic import BaseModel, Field

from clients import DEFAULT_MODEL, gemini_client
from extraction import ExtractedTask, SYSTEM_INSTRUCTION
from retry import call_with_retry


MODEL = DEFAULT_MODEL

COMPLETION_INSTRUCTION = """
ユーザーが既存タスクを完了したと明示した場合だけ、そのタスク名を
completed_task_titles に含めてください。既存タスクは次の一覧にある表記を
そのまま使ってください。予定・曖昧な発言・質問だけでは完了にしません。
"""


class DialogActions(BaseModel):
    tasks: list[ExtractedTask] = Field(default_factory=list)
    completed_task_titles: list[str] = Field(default_factory=list)


_client = gemini_client


def extract_dialog_actions(
    user_text: str, known_titles: list[str]
) -> tuple[list[ExtractedTask], list[str]]:
    """Return new tasks and explicitly completed task titles from a user turn."""
    titles_block = "\n".join(f"- {title}" for title in known_titles) or "(なし)"
    contents = (
        f"既存の未完了タスク:\n{titles_block}\n\n"
        f"ユーザーの発話:\n{user_text}"
    )
    response = call_with_retry(
        lambda: _client().models.generate_content(
            model=MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION + COMPLETION_INSTRUCTION,
                temperature=0,
                thinking_config=types.ThinkingConfig(thinking_budget=-1),
                response_mime_type="application/json",
                response_schema=DialogActions,
            ),
        )
    )
    result = DialogActions.model_validate_json(response.text)
    return result.tasks, result.completed_task_titles
