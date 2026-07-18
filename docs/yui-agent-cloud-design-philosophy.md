# yui-agent(クラウド版)の設計思想と再現性のある知見

「入力されなかったタスク」を対話から発見するクラウド版AI秘書エージェント。独り言・雑談からGeminiがタスクを抽出し、Firestoreの記憶で再言及を検出して優先度を自律昇格、Google Tasksに登録する。Cloud Scheduler駆動の自律バックグラウンドジョブが放置タスクを見直し、Google Search groundingで裏どり調査を添える。DevOps × AI Agent Hackathon(ファインディ主催/Google Cloud協賛)提出作品。ローカル版の[[desk-buddy-yuichan-design-philosophy|desk-buddy-YuiChan]]とは独立した設計・実装。

## 設計思想

### モジュール分割の理由

`docs/plan-hardening-v2.md`に明記された方針「判定ロジックは外部依存ゼロの純関数に切り出してからテストする」が一貫している。`priority.py`(優先度昇格)、`confidence.py`(しきい値フィルタ)、`dedup.py`(重複質問判定)、`matching.py`(タイトル突合)はいずれもGoogle依存を一切importしない純ロジックで、Gemini/Firestoreを呼ぶ関数はテストしづらいという実務的判断から意図的に分離されている。`rate_limit.py`と`retry.py`も同様に外部SDKへの依存を最小化している。

### セキュリティ・堅牢化の判断

- `auth.py`は`X-Yui-Token`(または`?token=`)で状態変更・課金系エンドポイントを保護。`--allow-unauthenticated`のまま公開すると「本人のGoogle Tasksへのタスク捏造」と「Geminiの無制限消費(コストDoS)」が起きるという脅威を明示している。
- `assert_token_configured()`はCloud Run環境(`K_SERVICE`検知)でトークン未設定なら起動自体を失敗させるfail closed設計。ローカル開発はfail open(トークン未設定なら素通し)という非対称設計を意図的に採用。
- `secrets.compare_digest`によるタイミング攻撃対策、BOM除去というWindows/PowerShell特有の運用トラブルへの目配りもある。
- Vertex AI/FirestoreはADC(Application Default Credentials)でAPIキーレス(`clients.py`)。Google TasksのみOAuth refresh tokenをSecret Manager経由で使用、CI/CDもWorkload Identity Federationでサービスアカウントキーを作らない(`docs/cicd-setup.md`)。
- `rate_limit.py`はプロセス単位インメモリ固定窓レート制限で、複数インスタンス間の状態共有はできないが「高コストエンドポイントを保護する補助的な制限」と割り切っている。
- `autonomous_review.py`/`agent_loop.py`のFirestoreクエリは意図的にサーバサイド絞り込みを避け(複合インデックス要求で本番を壊すリスク回避)、代わりに`.limit()`でスキャン件数だけ上限を設ける「安全側の防御的キャップ」を採用。
- `priority.py`の`promote`は`SYSTEM_ESCALATION_CEILING`でシステムが自律的に上げられる優先度上限を絞れる設計。`autonomous_review.py`は`last_reviewed_at`ガードで「毎回runで毎回+1され全部が最上位に張り付く」飽和バグを回避している。

### 自律レビュー(autonomous_review)の思想

`run_autonomous_review()`は放置(`STALENESS_HOURS`超過)タスクだけを対象に優先度を1段昇格させ、`RESEARCH_PRIORITY_THRESHOLD`(既定4)以上になったものだけGoogle Search groundingで裏どり調査(`research.py`)を添付する。ユーザーの指示なしに動く自律性と、暴走を防ぐ複数のガード(ceiling、staleness、last_reviewed_at)をセットで設計している。

### ハッカソン提出作品としての優先順位

`docs/self-review.md`は`hackathon-judge`スキルによる辛口自己採点(42/60→改善パスで47〜51/60)を記録し、「未認証公開エンドポイント」「テストゼロ」「捕捉精度の未実証」をTOP3弱点として明示、優先的に潰している。壁打ち・不在時検証・ローカル版との人格統合は`docs/vision.md`で明確に「実装しない」とスコープアウトし、対話品質と自律バックグラウンドの2点だけをMVPに絞る判断を下している。plan-hardening-v2/v3は「計画→実装→検証」というマルチエージェント運用で段階的に弱点を潰すプロセスを踏んでいる。

## 再現性のある知見

- **優先度スコアリング** — 1〜5の整数、`promote(current, step, ceiling)`で段階昇格+上限飽和を分離。「誰が昇格させるか(人間 vs システム)」で上限を変える`ceiling`パラメータ化は、自律性と暴走防止を両立する汎用パターン。
- **確信度による処理分岐** — `confidence.py`の`filter_confident(items, threshold, get=...)`は`get`引数でオブジェクト形状に依存しない純関数。高ノイズ経路(独り言)のみ閾値適用、高信号経路(直接発話)は適用しないという「入力の信頼度に応じてしきい値を変える」設計は他プロジェクトにも転用可能。
- **重複排除** — `dedup.py`の`normalize_text`(小文字化+空白除去)による完全一致判定は、エージェントが同じ質問を繰り返す退行を防ぐシンプルだが効果的な手法。`matching.py`は`endswith`による部分一致が誤マッチを起こした実バグを教訓に、正規化後の完全一致へ倒す判断をしている(コメントに失敗の経緯が明記されており再利用時の警告として有用)。
- **コストDoS対策** — 未認証公開エンドポイントを持つLLMバックエンドは「第三者によるLLM無制限消費」がリスクという認識のもと、共有トークン+fail closed起動チェック+レート制限の三層防御は、個人開発のCloud Run×LLMサービス全般に転用できるテンプレート。
- **Cloud Runでの認証設計** — `--allow-unauthenticated`を維持しつつアプリ層トークンで守る、Cloud SchedulerのみOIDC+ヘッダトークンの二重防御という組み合わせは「デモのURL共有しやすさ」と「安全性」のバランスを取る現実的パターン。
- **リトライ設計** — `retry.py`の`call_with_retry`は`sleep`を注入可能にしてテスタブルにし、「失敗時応答が返らないため失敗後リトライは二重課金にならない」という明示的な安全性の理由付けが妥当性の判断材料として有用。
- **精度の実証ハーネス**(`bench/`ディレクトリ) — ラベル付きサンプル+precision/recall/false_positive_rate算出+しきい値スイープをレポート化する仕組みは、LLM抽出タスクの精度を「未実証」から「実測値」に変える再現可能な手法。

## まとめ

yui-agent(クラウド版)の核心は、判定ロジックを外部依存ゼロの純関数に切り出してテスト可能にする設計と、自律性(優先度昇格・裏どり調査)にceiling/staleness/last_reviewed_atといった暴走防止ガードを必ずセットで設計する姿勢にある。個人開発のCloud Run×LLMサービスにおける「コストDoS対策」「fail closed起動チェック」は特に再利用価値が高い。
