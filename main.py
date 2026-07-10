"""Yui Cloud Agent — 「入力されなかったタスク」を発見する対話エージェント。

MVP パイプライン:
    対話入力 → Gemini(タスク抽出・優先度・理由) → Firestore(記憶・優先度昇格) → Google Tasks
"""
from fastapi import FastAPI

app = FastAPI(title="Yui Cloud Agent")

APP_VERSION = "0.0.1"


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "agent": "yui", "version": APP_VERSION}
