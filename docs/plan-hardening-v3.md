# 実装計画 v3 — 更新TOP3の改善（Fable計画 → Codex実装 ＋ ライブ実行）

47→51/60 の残TOP3を潰す。**Codexが実装**、**ADC/gcloud/ブラウザが要る部分は人間側(Claude main)がライブ実行**。

## 全体の検証コマンド（Codexは各ステージ後に実行・常に緑）
```bash
cd C:/Users/1kkim/projects/yui-agent
uv run --with ruff ruff check .
uv run --with-requirements requirements-dev.txt --with httpx pytest -q
```
純ロジックは必ず `tests/` にユニットテストを追加（既存方針）。

---

## Stage A（Codex）— 捕捉精度ハーネスの「数字を出せる」化（弱点#1・最重要）

**目的**: 実行すると precision / recall / **false_positive_rate** と、しきい値スイープを**Markdownレポート**で吐く。
実測値をピッチに載せられる形にする（実行自体は人間側=ADC必須）。

**変更**:
- `bench/extraction_samples.json`: 12→**20件**に増やす（task10 / none10）。noneに「STT誤り断片」「タスクでない雑談」
  「ゆい自身への発話」「曖昧すぎ」を厚めに。実在の独り言らしい日本語で。
- `bench/extraction_metrics.py`（純・既存）: 変更不要か、必要なら `format_report(scored, threshold)` を追加して
  Markdown表文字列を返す純関数にする（テスト可能に）。
- `bench/extraction_eval.py`: 
  - `--threshold`（既定0.6）で confidence フィルタ適用後の予測も評価。
  - `--sweep` で 0.0/0.3/0.5/0.6/0.7/0.8 のしきい値スイープ表を出す。
  - `--out bench/results/extraction-eval.md` に Markdown レポートを書き出す（標準出力にも要約）。
  - **実Gemini必須なのでCIでは走らせない**。`python -m compileall bench/extraction_eval.py` が通ることだけ担保。
- テスト: `tests/test_extraction_metrics.py` に `format_report` のテストを追加（純関数なら）。

---

## Stage B（Codex）— スケールの防御的キャップ（弱点#3: N-scan）

**方針（重要・安全側）**: サーバサイド絞り込み（`where status != "done"` 等）は**複合インデックスが必要になり本番を壊す**
リスクがある。現状の「取得してPythonで絞る」はインデックス不要の意図的設計。**そこは変えない**。
代わりに**無制限スキャンに上限(limit)を足すだけ**にする（インデックス不要・安全）。

**変更**:
- `agent_loop.list_tasks()`: `order_by(...).limit(LIST_LIMIT)` を追加（既定200・env `YUI_LIST_LIMIT`）。
- `autonomous_review.run_autonomous_review()`: `where("priority","<",MAX_PRIORITY).limit(REVIEW_LIMIT)` を追加（既定500・env）。
- コメントで「サーバサイド絞り込みを避ける理由＝インデックス不要設計」を明記。
- 挙動を変えない純ロジックは無いが、`main.py`/フローに影響が出ないことを確認（テスト緑維持）。

---

## Stage C（Codex）— カナリアデプロイ＋ERRORアラート手順（弱点#3: canary/alert）

### C1. カナリア（`.github/workflows/deploy.yml`・安全・fail-safe）
現状は `gcloud run deploy --source .`（即100%）。これを**段階化**：
1. `gcloud run deploy yui-agent --source . ... --no-traffic --tag=canary`（新リビジョンを0%トラフィックで作る）。
2. カナリアURL（`gcloud run services describe --format="value(status.traffic.filter(tag=canary).url)"` 等）に対し
   `/health` が 200 を返すことをスモーク（curl -f）。**失敗したら migrate せず job を落とす**（旧リビジョンが100%のまま＝安全）。
3. スモーク成功時のみ `gcloud run services update-traffic yui-agent --to-latest`（100%移行）。
- 既存の `--allow-unauthenticated --set-secrets=YUI_APP_TOKEN=...` は保持。
- **絶対条件**: この変更で通常デプロイが壊れないこと。gcloudのtag/traffic構文が不確実なら、
  最小構成（no-traffic→health→to-latest）に留め、凝った重み付けはしない。

### C2. ERRORアラートのプロビジョニング手順スクリプト
- `scripts/setup_error_alert.ps1`（実行は人間・冪等志向）: 
  - メール通知チャンネル作成（`gcloud beta monitoring channels create --type=email --channel-labels=email_address=<...>`、既存なら再利用）。
  - ログベースアラートポリシー作成（`resource.type=cloud_run_revision AND severity>=ERROR AND resource.labels.service_name=yui-agent`）。
  - 冪等性: 同名が既にあればスキップする旨コメント。
- `docs/cicd-setup.md` の既存アラート節から、このスクリプトを指す1行に整理。

---

## Stage D（人間=Claude main がライブ実行・Codex対象外）
- **D1 精度実測**: `GOOGLE_CLOUD_PROJECT=yui-agent-2026` ＋ADCで `python bench/extraction_eval.py --sweep --out bench/results/extraction-eval.md` を実行し、
  precision/FP率の実数を得る → `docs/self-review.md` と（あれば）demo-script に記載。
- **D2 アラート実配備**: `scripts/setup_error_alert.ps1` を gcloud フルパスで実行（分類器にブロックされたらユーザーに委ねる）。
- **D3 実機デモ検証（弱点#2）**: Claude-in-Chrome で本番URL `?token=` を開き、orb状態・ダッシュボード・API往復を実機確認・スクショ。
  （音声/マイクの自動化は不可＝そこは手動リハに委ねる旨を記録。）

---

## Stage E — 総合検証 + 自己批判
- ruff / pytest 緑、compileall 緑。触ったファイルを開き直す。
- カナリア変更は「壊れても旧リビジョンが残る」ことをコメント/構造で担保できているか。
- `docs/self-review.md` を実施状況で更新。

## 対象外（明示）
- Firestore サーバサイド絞り込み（複合インデックス要）＝インデックス不要設計を維持するため**やらない**。
- 音声/マイクのE2E自動化＝ブラウザ自動化では非現実的。手動リハに委ねる。
