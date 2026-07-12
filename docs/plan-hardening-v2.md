# 実装計画 v2 — TOP3弱点の改善（Fable計画 → Codex実装）

セルフ審査(47/60・入賞圏)の残る弱点を潰す。Codex がこの計画に沿って実装し、
各ステージの「検証コマンド」が通ることを確認する。**ruff と pytest は常に緑を保つ。**

## 全体の検証コマンド（各ステージ後に実行）

```bash
cd <リポジトリのクローン先>/yui-agent
uv run --with ruff ruff check .
uv run --with-requirements requirements-dev.txt --with httpx pytest -q
```

新しい純ロジックは必ず `tests/` にユニットテストを追加する。Google依存
（`from google...`）を import する関数はテストしづらいので、**判定ロジックは
外部依存ゼロの純関数に切り出して**からテストする（既存の matching/priority/dedup と同方針）。

---

## Stage 1 — アンビエントUIの状態一目表示（弱点#2）

**目的**: 「今聞かれてる？」の不安を消す。状態を一目で分かるラベルにし、会話継続窓の残り秒を出す。

**変更**: `static/index.html` のみ。

- 各状態のステータス文言を、より明快に：
  - ambient（待機）: `🎧 聞いてるよ（呼ぶときは「ゆい」）`
  - captured: `📝 メモしたよ`
  - thinking: `💭 考えてる…`
  - speaking: `💬 話してる…`
  - off: `オフになっています`
- **会話継続窓のカウントダウン**: `conversationActiveUntil` が有効な間、ambient表示のときだけ
  ステータスを `💬 会話中（名前なしでOK・あと○秒）` にして毎秒更新する。
  - 実装: `setInterval` を1秒間隔で回す ticker を追加。`setState('ambient')` 時、かつ
    `Date.now() < conversationActiveUntil` なら会話中ラベル＋残り秒（`Math.ceil((until-now)/1000)`）を表示。
    それ以外の ambient は通常の待機ラベル。thinking/speaking/captured/off の間は ticker は statusEl を触らない。
  - `disableAmbient()` で ticker を `clearInterval` する。二重生成しないよう単一の `tickerTimer` 変数で管理。
- 既存の `apiFetch`/トークン処理・VAD・録音ロジックは変更しない。

**検証**:
```bash
# <script>ブロックを抽出して構文チェック（HTMLは node --check 不可のため）
node -e "const fs=require('fs');const h=fs.readFileSync('static/index.html','utf8');const m=h.match(/<script>([\s\S]*?)<\/script>/);new Function(m[1]);console.log('index.html script OK')"
```
加えて、`聞いてるよ` と `会話中` の文言が `static/index.html` に存在すること（grep）。

---

## Stage 2 — research/draft の自己検証（弱点#3・最重要#1を 8→9）

**目的**: エージェントが research/draft した結果が「本当に前進に役立ったか」を1回だけ自己評価し、
不十分なら勝手に in_progress にせず、ユーザーに聞く(ask)か様子見(monitor)へ落とす。

**新規純モジュール** `agent_verify.py`（外部依存ゼロ）:
```python
def plan_after_verification(note, sufficient, followup_action, question, asked_questions):
    """自己検証の結果から doc への update と分類(outcome)を決める純ロジック。

    - sufficient=True                      → outcome="progressed",
        update={"status":"in_progress","agent_notes":note,"pending_question":None}
    - sufficient=False かつ followup_action=="ask" かつ question があり
      is_duplicate(question, asked_questions) が False
                                           → outcome="asked",
        update={"status":"needs_input","pending_question":question,
                "asked_questions":asked_questions+[question]}
    - それ以外（monitor / ask不可 / 質問重複）→ outcome="monitor",
        update={"status":"open","agent_notes":note}   # noteは参考に残すが前進扱いにしない
    戻り値: {"outcome": str, "update": dict, "question": str|None}
    """
```
`is_duplicate` は既存 `dedup.py` を import して使う（純のまま）。

**`agent_loop.py` を改修**:
- `Verification(BaseModel)`: `sufficient: bool`, `followup_action: str = ""`(""/"ask"/"monitor"), `question: str = ""`。
- `_verify(title, reason, action, note) -> Verification`: Vertex Gemini(temp0, response_schema=Verification)。
  system instruction: 「エージェントが action(research/draft) で作った note が、このタスクを実際に
  前進させる具体的で有用な内容かを判定。不十分なら followup_action(ask/monitor) と、ask の場合は
  ユーザーが答えやすい具体的な question を1つ返す」。
- `run_agent_loop` の research/draft 分岐を変更：note生成後に `_verify` を呼び、
  `plan_after_verification(note, v.sufficient, v.followup_action, v.question, asked_questions)` で分岐。
  - outcome=="progressed" → progressed に追加（従来どおり）。
  - outcome=="asked" → asked に追加。
  - outcome=="monitor" → どちらにも追加しない（前進扱いにしない）。
  - update を doc に反映。`upsert_task` の reason 追記は従来の agent_notes / pending_question 分岐を踏襲。
- ask 分岐（diagnose が最初から ask）は現状維持（既に dedup 済み）。

**テスト** `tests/test_agent_verify.py`:
- sufficient=True → progressed / status in_progress。
- sufficient=False, followup=ask, 新規question → asked / needs_input / asked_questions に追加。
- sufficient=False, followup=ask, question が asked_questions と重複 → monitor。
- sufficient=False, followup=monitor → monitor / status open。

---

## Stage 3 — 抽出confidence + 精度の実証ハーネス（弱点#1・最大残リスク）

**目的**: 「独り言→タスク」の誤爆(false positive)を、しきい値で機械的に抑え、かつ**精度を測定可能**にする。

### 3a. confidence フィールド + しきい値フィルタ
- `extraction.py`: `ExtractedTask` に `confidence: float = Field(ge=0.0, le=1.0, description="このタスク抽出の確信度(0-1)")` を追加。
  SYSTEM_INSTRUCTION に「各タスクに確信度 confidence(0-1) を付ける。独り言は聞き取り誤りを含むため、
  少しでも曖昧なら低め(<0.6)にする」を追記。
- **新規純モジュール** `confidence.py`:
  ```python
  def filter_confident(items, threshold, get=lambda x: x.confidence):
      """confidence が threshold 以上の要素だけ返す純関数。"""
  ```
- `main.py` の `/process`（独り言＝高ノイズ経路）のみ、`extract_tasks` 結果を
  `filter_confident(extracted.tasks, CONFIDENCE_THRESHOLD)` で絞ってから登録する。
  `CONFIDENCE_THRESHOLD = float(os.environ.get("YUI_CONFIDENCE_THRESHOLD", "0.6"))`。
  `/chat`（ユーザーがゆいに話しかけた経路＝高信号）はしきい値を**かけない**（従来どおり）。
- テスト `tests/test_confidence.py`: threshold 未満を除去 / 境界(==threshold は残す) / 空リスト。

### 3b. 抽出精度の評価ハーネス（実証）
ローカル版YuiChanの bench と同方針。**実Gemini(ADC)で走る独立スクリプト**＋純採点。
- `bench/extraction_samples.json`: ラベル付き独り言 12件程度。各 `{"utterance": str, "expect": "task"|"none", "note": str}`。
  カバー: 明確なタスク / 期限付き / 複数タスク / 曖昧 / STT誤り断片 / タスクでない雑談 / ゆい自身への発話。
- **新規純モジュール** `bench/extraction_metrics.py`:
  ```python
  def score(predictions, labels):
      """予測(タスク有=True/無=False)と正解から precision/recall/false_positive_rate 等を返す純関数。
      戻り: {"tp","fp","fn","tn","precision","recall","false_positive_rate","accuracy","n"}"""
  ```
  ゼロ除算は 0.0 を返す。
- `bench/extraction_eval.py`: samples を読み、`extract_tasks` を実行、`len(tasks)>0` を予測とし
  `score` で集計して表示。`--threshold` で confidence フィルタ後の予測も比較表示できると尚可。
  （このスクリプトは実Gemini必須なので CI では走らせない。ローカル手動で `python bench/extraction_eval.py`。）
- テスト `tests/test_extraction_metrics.py`: 既知の predictions/labels で precision/recall/FP率を検算。

---

## Stage 4 —（任意）transient リトライ

**目的**: Gemini/Firestore の一時的エラー(503/429/timeout)で即failせず、数回リトライ。

**新規純モジュール** `retry.py`:
```python
def call_with_retry(fn, attempts=3, is_transient=<default>, sleep=time.sleep, base_delay=0.5):
    """fn() を呼び、is_transient(exc) が True の例外なら指数バックオフで最大 attempts 回リトライ。
    非一時例外は即再送出。全部失敗したら最後の例外を送出。sleep は注入可能(テスト用)。"""
```
`is_transient` の既定は、例外文字列に "503"/"429"/"deadline"/"unavailable"/"timeout" 等を含むか（保守的）。
- 適用: `extraction.py` / `chat.py` / `agent_loop.py` / `autonomous_review.py` の
  `client.models.generate_content(...)` 呼び出しを `call_with_retry(lambda: client.models.generate_content(...))` で包む。
  ※ generate_content は失敗時に応答が返らないので、失敗後のリトライは二重課金にならない。
- テスト `tests/test_retry.py`: 2回失敗→3回目成功 / attempts 到達で送出 / 非一時例外は即送出 / sleep 注入で待たない。

---

## Stage 5 —（運用/doc）ERROR ログのアラート

**目的**: obs.py の構造化ログ(severity=ERROR)に対する Cloud Monitoring ログベースアラートを1本張る手順。

**変更**: `docs/cicd-setup.md` に新セクション追加（gcloud コマンド例）。コードは変更しない。
- ログベース指標 or `gcloud alpha monitoring policies create` で
  `resource.type=cloud_run_revision AND severity>=ERROR AND resource.labels.service_name=yui-agent`
  に対する通知チャンネル付きアラートを作る手順を記載。実行はユーザー本人（gcloud 権限が要るため）。

---

## Stage 6 — 総合検証 + 自己批判

- 全体の検証コマンド（ruff + pytest）が緑。`python -m compileall -q .` も緑。
- 触った各ファイルを開き直し、1つのエラーパスを説明できること。
- `docs/self-review.md` のチェックリストを実施状況で更新。

## 対象外（今回やらない）
- URLクエリ決定値のデフォルト反映 … リハ実測が要る運用タスク。
- yui-app-token シークレット作成 … GCP操作、ユーザー本人が実施（`cicd-setup.md §4.5`）。
