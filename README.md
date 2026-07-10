# Yui Cloud Agent

**「入力されなかったタスク」を発見する対話エージェント。**

既存ツールは "入力したタスク" を管理する。Yui は独り言・思いつき・30秒メモといった雑な対話から、タスクを抽出し、優先度と理由を自律判断して Google Tasks に登録する。過去の言及を記憶し、「前にも言ったのに終わってないタスク」の優先度を昇格させて指摘する。

> DevOps × AI Agent Hackathon（ファインディ主催 / Google Cloud 協賛）提出作品

## アーキテクチャ（MVP）

```
対話入力（テキスト → 将来は音声）
  ↓
Gemini: タスク抽出・優先度スコア・理由生成（構造化JSON, temperature=0）
  ↓
Firestore: 履歴保存 → 過去言及と突合 → 優先度昇格判定
  ↓
Google Tasks API: 登録
```

すべて Cloud Run 上で動作。

## 競合との違い

- **Circleback 等の会議系ツール**: 会議が前提。Yui は会議の外（独り言・思いつき）を拾う
- **既存 ToDo アプリ**: 単発の入力を管理する。Yui は履歴を跨いで判断し、忘れられたタスクを自分から昇格させる

## ローカル実行

```bash
pip install -r requirements.txt
uvicorn main:app --reload
# http://127.0.0.1:8000/health
```

## デプロイ

```bash
gcloud run deploy yui-agent --source . --region asia-northeast1 --allow-unauthenticated
```

## ロードマップ

- Speech-to-Text による音声メモ入力
- ローカル版 YuiChan（デスクバディ）との人格・記憶統合
- 毎朝ブリーフィング / 複数サービス連携 / メモからの調査・計画立案
