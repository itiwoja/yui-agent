# セルフ審査＆本番前チェックリスト — Yui Cloud Agent

> DevOps × AI Agent Hackathon（ファインディ主催 / Google Cloud 協賛・最終ピッチ 8/19）
> `hackathon-judge` スキルによる辛口セルフ採点（2026-07-11 実施）。
> **辛口基準**: ここで X点 ≒ 本番はもっと辛い、を前提に読む。

---

## 採点サマリ

| 項目 | 点 | 主因 |
|------|---:|------|
| 1. AIエージェント中心性（最重要） | 8/10 | ループの深さ1段・自己検証なし |
| 2. 課題アプローチ力 | 8/10 | 常時マイク＋独り言仮説が未検証（N=1） |
| 3. ユーザビリティ | 6/10 | アンビエントマイクのメンタルモデル・環境依存 |
| 4. 実用性・体験価値 | 7/10 | 捕捉精度に全依存・エスカレーション飽和 |
| 5. 実装力 | 6/10 | テストゼロ・未認証公開・endswith誤マッチ |
| 6. DevOps実践度 | 7/10 | CIに品質ゲートなし・観測性なし |
| **合計** | **42/60** | 「足りない」上端。穴は軽い工数で塞げる |

**判定**: コンセプト・スタックは入賞圏（45〜53）ポテンシャル。実装力とUXの穴で自滅的に失点中。
下の🔴を潰すだけで現実的に **48〜50（入賞圏）** へ届く。

> **進捗（2026-07-11 改善パス）**: 🔴TOP3・⚡すぐ効く・🏗の大半を実装済（下のチェック参照）。
> テスト 0→**26本**（+ruff+CI）、未認証穴を塞ぎ、エスカレーション飽和バグと **tzdata起動クラッシュ**を修正。
> 推定は実装力6→8・DevOps7→8・UX6→7へ改善見込みで **合計 ~47〜49（入賞圏入り）**。
> 残りは主に運用/リハ（会場調整・デモ台本での精度提示）と、任意の自己検証（Gemini課金増）。
> **本番前の必須手順**：`yui-app-token` シークレット作成（`cicd-setup.md §4.5`）を**次のデプロイ前に**実施すること
> （未作成だとデプロイが fail closed で止まる＝穴が開いたまま出るより安全だが、手順漏れに注意）。

---

## 🔴 最優先で塞ぐ（落ちる理由 TOP3）

- [x] **未認証の公開エンドポイントを塞ぐ** ＝最重要 → **完了**
  - `auth.py`：`X-Yui-Token` 共有トークンゲート（`is_authorized` 純ロジック＋`require_app_token` 依存）。
    保護対象＝`/process /chat /tts /transcribe /autonomous-review /tasks /tasks/*`（`/health`・静的UIは開放）。
  - `deploy.yml`：`--set-secrets=YUI_APP_TOKEN=yui-app-token:latest`（未設定なら**デプロイ失敗＝fail closed**）。
  - フロント：`?token=` → sessionStorage → `X-Yui-Token` 付与（index/dashboard 両方）。
  - Scheduler：ヘッダ付与に変更（`cicd-setup.md §4.5 / §5`）。
  - テスト：401配線 4本＋トークン純ロジック 4本。
- [x] **自動テストを追加** → **完了**（26本・ruff・pytest を CI `check` ジョブへ）
  - `matching`(6) `priority`(5) `auth`(4) `dedup`(5) `obs`(2) ＋ エンドポイント401配線(4)。
  - CI：`requirements-dev.txt` 導入 → `ruff check` → `compileall` → `pytest`。
- [x] **捕捉精度＆アンビエントマイクUXの信頼担保** → **部分完了**
  - [x] 誤タスク **ワンタップ取消**（dashboard「取消」＋`DELETE /tasks/{id}`＝Firestore+Google Tasks両削除）。
  - [ ] （デモ時）抽出confidenceの可視化・false-positive を出さない台本での通し（＝運用/リハ側）。

---

## ⚡ すぐ効く（軽くて効く・まず全部やる）

- [x] `/autonomous-review` `/chat` `/process` に**認証** → 🔴TOP1解消（上記）
- [x] CIに **`pytest`＋`ruff`** を追加、テスト → 🔴TOP2解消＋「まわす」を本物に
- [x] **誤タスク ワンタップ取消** ＋ `endswith`→**正規化完全一致**（`matching.titles_match`）
  - `tasks_client.py`（upsert/complete/**delete**）・`main.py`（completion突合）を全て置換。回帰テスト有り。
- [x] orbに**状態ラベル**＋初回ガイド → **既に実装済**（`index.html` の `statusEl` 各状態＋`yui_initial_hint_shown`）。追加不要と確認。
- [ ] 会場調整（`?silence=`/`threshold=`）の**決定値をデフォルト反映** → **リハ時タスク**（コードでなく運用）。

---

## 🏗 重いが効く（余力があれば・最重要項目を押し上げる）

- [x] **エージェントループに自己記憶** → **完了**（`agent_loop.py`＋`dedup.py`）
  - `task_mentions.asked_questions[]` を持ち、`is_duplicate` で**同じ質問の再発火を抑止**（回答後 open 復帰時の無限リ質問を遮断）。
  - [ ] research/draft の**有用性 自己検証**（＝もう1回Gemini評価）は Gemini課金増のため保留（YAGNI／必要になったら）。
- [x] **エスカレーション飽和対策**（`autonomous_review.py`）→ **完了**
  - `last_reviewed_at` ガードで**滞留期間ごと最大1回**に（30分毎runで毎回+1する飽和バグを修正）。
  - `SYSTEM_ESCALATION_CEILING`（env・既定MAX）で🔴を人間の緊急に残せる。純ロジック`priority.promote`＋テスト。
- [x] Gemini呼び出しを **try/except で graceful degradation** → **完了**
  - `/chat` 失敗時はキャラ内で謝る応答（音声UIが無言にならない）、`/process` 失敗時は空で返す（待機継続）。
  - リトライは partial-success 二重課金リスクを避け、まず graceful のみ（必要なら genai 側の retry 設定で）。
- [x] **構造化ログ**（`obs.py`）→ **完了**。`print` を severity 付き1行JSONへ置換（Cloud Loggingで重大度フィルタ/アラート可能）。transcribe は生文でなく文字数のみログ（プライバシー）。

---

## 🔧 改善パス v2（2026-07-11・Fable計画→Codex実装）— 残TOP3を潰す

計画 `docs/plan-hardening-v2.md`（Fable段階計画）→ Codex実装 → ruff/pytest検証。テスト 26→**40本**（+14）。

- [x] **弱点#1 捕捉精度の抑制＋実証**（最大残リスク）
  - `extraction.py` に `confidence(0-1)` フィールド＋プロンプト指示。`/process`（独り言＝高ノイズ）のみ
    `confidence.filter_confident` で `YUI_CONFIDENCE_THRESHOLD`(既定0.6) 未満を除去（`/chat` は非適用）。
    構造化出力スキーマが confidence を強制するので、欠落時は抽出失敗→空返し＝**誤タスクを作らない安全側**。
  - **精度評価ハーネス**: `bench/extraction_metrics.py`(純・precision/recall/FP率) ＋ `bench/extraction_samples.json`
    (12件・task6/none6) ＋ `bench/extraction_eval.py`(実Gemini手動実行)。**精度を測定可能化**＝「未実証」に回答。
- [x] **弱点#2 状態一目表示**（`static/index.html`）
  - `🎧 聞いてるよ（呼ぶときは「ゆい」）` / `📝 メモしたよ` / `💭 考えてる…` / `💬 話してる…`。
  - **会話継続窓のカウントダウン** `💬 会話中（名前なしでOK・あと○秒）` を毎秒更新（ambient時のみ・ticker start/stop検証済）。
- [x] **弱点#3 research/draft 自己検証**（最重要#1を 8→9）
  - `agent_verify.plan_after_verification`(純) ＋ `agent_loop._verify`(Gemini)。note が前進に不十分なら
    **in_progress にせず** ask（新規質問のみ・重複は monitor）/ monitor へ降格。
- [x] **軽い実装: transient リトライ**（`retry.call_with_retry`・stdlib）
  - 一時障害(503/429/timeout等)を指数バックオフで最大3回。extraction/chat/agent_loop/autonomous_review の
    `generate_content` を包む（失敗後リトライ＝二重課金なし）。sleep注入でテスト済。
- [x] **軽い実装: ERROR ログのアラート**（`docs/cicd-setup.md`・運用手順）

**検証（私が独立実行）**: `ruff check .` 緑 / `compileall`（bench eval含む）緑 / フル `pytest` **40 passed**。
既存の飽和ガード(`last_reviewed_at`/`SYSTEM_ESCALATION_CEILING`)・認証・記憶ロジックに**回帰なし**を確認。

**残（コード外）**: 会場調整の決定値デフォルト反映＝リハ実測待ち。デモで false-positive を出さない台本＝運用。

---

## 🐞 テストで発見した本番バグ（副産物）

- [x] **`ZoneInfo("Asia/Tokyo")` が import 時にクラッシュ**（`calendar_client.py`）
  - IANA tzデータの無い環境（Cloud Run `python:3.12-slim` 等）で `ZoneInfoNotFoundError` → **アプリ全体が起動不能**になり得た。
  - `requirements.txt` に `tzdata` を追加して解消。テスト整備が無ければ提出直前まで潜伏した可能性大。

---

## 審査員別・刺さる／刺さらない

### VPoE（技術・組織・運用）
- ✅ WIFキーレスCI/CD・ADC・Secret Manager・最小権限SA・クリーンなモジュール分割
- 🔻 **テストゼロ・未認証公開・観測性なし・直本番デプロイ** ← 最大失点源。「すぐ効く」を全部やって初めて土俵に乗る

### Developer Advocate（Google Cloud活用の妙・発信性）
- ✅ **8サービスの噛み合わせ**、Search grounding＋構造化出力、「なぜADK不使用か」を言語化済（ロードマップで回収＝good）
- 🔻 ADK／Agent Builder不使用は必ず問われる（回答準備済み＝強い）。**アーキ図・デモ録画**など発信素材を当日までに整える

### CPO（課題・体験価値・プロダクト筋）
- ✅ 「入力されなかったタスクを発見する」の一言、続かない根本原因への回答、秘書メタファ、ループが閉じる（done同期）
- 🔻 常時マイクの心理的ハードル、N=1検証、捕捉精度の不確実さ

---

## 30秒ピッチ（審査員に刺す版）

> 「タスク管理アプリ、続いたことありますか？ 僕は一度もない。理由は明確で、**忙しい時ほど"入力"ができない**から。
> クラウドゆいは、入力しなくても聞いています。作業中の独り言を Gemini が拾ってタスク化し、Firestoreの記憶で
> "前にも言ったのに終わってない"を見つけて**勝手に優先度を上げ、Google検索で裏どりし、分からないことは質問してくる**。
> 全部 Cloud Run＋Vertex AI で動き、pushすればWIFキーレスCIが本番へ届ける。**管理ツールじゃなく、秘書です。**」

---

## 総括

提出判断・スタック選定・課題設定は入賞圏の質。落としているのは**思想ではなく詰め**（認証・テスト・捕捉精度）で、
いずれも軽い工数で塞げる穴。本番までに「すぐ効く」4点を全部やれば辛口採点でも **48〜50（入賞圏）** が見える。
**未認証公開だけは放置厳禁** — 技術点がいくら高くても、審査員が本番URLを叩いた瞬間に評価が反転する。
