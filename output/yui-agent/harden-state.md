# harden-state — yui-agent

## メタ
- 開始: 2026-07-12
- 対象: C:\Users\1kkim\projects\dev\yui-agent（全体）
- モード: **auto**（ユーザー指定 2026-07-12）。絶対停止線のみ停止
- スコープ: **全面再監査**（ユーザー指定）
- --fix 下限: HIGH（既定 = CRITICAL+HIGH を修正）
- 周回上限: 5 / ループ: あり（loop-until-dry: 2周連続 新規CRITICAL/HIGHゼロで終了）
- 予算: 未指定（開始時に概算提示・続行確認）

## ベースライン（Phase 0）
- git: master, クリーン（HEAD 7c257dc）
- テスト: `python -m pytest -q` → **106 passed**, 2 warnings, 3.39s（緑）
- 規模: Python ~2,613行（26モジュール）+ static/ ~1,001行（index.html 591 / dashboard.html 410）
- スタック: FastAPI + Cloud Run / Firestore / Gemini / STT(Chirp) / TTS / Cloud Tasks / OTel(Cloud Trace) / Vertex Embeddings

## 前回監査との関係
- 2026-07-11 に 9-agent 全面監査済（`.ai/audit_summary.md`）。CRITICAL 8件・HIGH 15件は Brief #1〜15 で概ね修正済み。
- MEDIUM/LOW バックログが audit_summary.md に残存。
- 前回監査以降の新規コード（約 +1,920 行）: 分散トレーシング(tracing.py)、/converse ストリーミング統合、streaming TTS、Cloud Tasks 化(background_queue/tasks 実行)、質問ループ音声完結(dialog_actions)、Vertex Embeddings 意味的再言及(embeddings.py/memory_store)、UI刷新(static/*)、sentence_split。

## ラウンド記録

### Round 1 — 監査完了（2026-07-12）
10 agent 完了（auditor/security/code/silent-failure/perf/observability/tests/design/a11y/python）。subagent 消費 約94万トークン。

#### 統合 CRITICAL/HIGH（重複排除済み・修正対象）
| # | 重大度 | 統合元 | 内容 | Brief |
|---|---|---|---|---|
| R1-1 | CRITICAL | SF1+PY1 | /converse の context_future 未保護（正常系 :425 は素500、413分岐 :371-376 は無ログ握りつぶし） | A |
| R1-2 | CRITICAL | O1+O2 | /tasks/* 3endpoint と /process・/chat の record_and_resolve が obs.error 圏外 | A |
| R1-3 | CRITICAL | CR-2+T8 | /converse クライアントフォールバック×finalize 非冪等 → 同一発話の二重確定（履歴・mention_count・Google Tasks・課金） | B |
| R1-4 | CRITICAL | PA1 | Google Tasks N+1（audit_summary の C5 誤記載を訂正の上修正） | C |
| R1-5 | CRITICAL | P1 | Gemini ストリーム×TTS 完全直列 → プロデューサ/コンシューマ化 | C |
| R1-6 | CRITICAL | D1 | アクセント #5E6AD2 = Linear 実ブランドカラー | D |
| R1-7 | HIGH | SEC1+PA3 | /internal/finalize-turn レート制限なし | B |
| R1-8 | HIGH | SEC2 | finalize-turn の reply 無検証永続化（履歴汚染）。完全対策=OIDC分離は要インフラ変更→冪等化+レート制限で部分緩和し、OIDC移行は要手動バックログ | B(部分) |
| R1-9 | HIGH | SF4+PY6 | background_queue の設定ミスと transient の混同・非永続フォールバックの無音喪失 | A |
| R1-10 | HIGH | SF3+O6+PY7 | embed_text: 例外詳細欠落・retry なし・計装なし | A |
| R1-11 | HIGH | O3 | 401/429 の無ログ | A |
| R1-12 | HIGH | O4+O5 | Cloud Tasks の request_id 相関断絶・finalize 経路/リトライ回数不記録 | A |
| R1-13 | HIGH | O7 | finalize_turn 内ループ per-item 保護なし・title 不記録 | A |
| R1-14 | HIGH | CR-3 | /chat・/process の record_and_resolve 同期実行（Embeddings 追加でレイテンシ回帰） | A |
| R1-15 | HIGH | P3+CR-1 | TTS 部分成功後フォールバックで二重再生 | C |
| R1-16 | HIGH | P4 | ThreadPoolExecutor 毎回生成（入れ子） | C |
| R1-17 | HIGH | P8+PY3 | tts._get_client ロックなし | C |
| R1-18 | HIGH | PA4 | calendar_client シングルトン化 | C |
| R1-19 | HIGH | PA2 | セキュリティヘッダ + audio Content-Type 検証 | B |
| R1-20 | HIGH | PY2+CR-M | _resolve_remention 重複統一 | A |
| R1-21 | HIGH | PY4 | 公開関数の型注釈欠落（setup_tracing/stream_synthesize/stream_reply/fetchers） | A |
| R1-22 | HIGH | SF2+SF8 | dashboard 偽成功アナウンス・ボタン恒久死・load() 無防備 | D |
| R1-23 | HIGH | A1 | :focus-visible コントラスト不足 | D |
| R1-24 | HIGH | D2 | high-priority 枠線が不可視（機能死） | D |
| R1-25 | HIGH | D3+D5 | complete-button hover なし / セクション h2 色未展開 | D |
| R1-26 | HIGH | D4+A2 | --quiet コントラスト AA 未達 | D |
| R1-27 | HIGH | T1+T2 | answer_question / run_agent_loop 分岐テストゼロ | E |
| R1-28 | HIGH | T3+T4 | /converse ミッドストリーム失敗・STT失敗・413 テストなし | E |

#### 修正見送り（要検証/要手動）
- P2（TTS 1ストリーム複数input統合）: Cloud TTS API 仕様の確認が先 → バックログ
- SEC2 完全対策（Cloud Tasks OIDC + ingress 制限）: インフラ変更を伴うため要手動 → バックログ
- H10系（min-instances 等の課金判断）: 対象外

#### Brief 実行順
A: バックエンド正確性+可観測性 → B: セキュリティ → C: パフォーマンス → D: フロントエンド → E: テスト補強。各 Brief 後に pytest 緑確認。

#### Phase 3 進捗
- Brief A (#16 backend): **完了・検証 PASS・コミット 7ad7575**。Codex 新規テスト2件の SimpleNamespace→ExtractedTask 修正と、既存 embedding テストの期待値更新（実装改善に追従）は Claude が実施。117 passed / ruff 緑。
- Brief D (#17 frontend): **完了・検証 PASS・コミット 7ad7575**（R1-6/22/23/24/25/26）。
- Brief B (#18 security): **完了・検証 PASS・コミット ad7829e**（R1-3/7/8部分/19。turn_id 冪等化・レート制限・ヘッダ・415。122 passed）。
- Brief C (#19 perf): **完了・検証 PASS・コミット 59eabab**（R1-4/5/15/16/17/18 + P5/P7。パイプライン化・N+1キャッシュ・ロック統一。125 passed / ruff 緑）。
- Brief E (#20 tests): **完了・検証 PASS・コミット 36aaca7**（R1-27/28。midstream テストの文終端修正は Claude。134 passed）。

### Round 1 修正まとめ
コミット: 7ad7575 (A+D) → ad7829e (B) → 59eabab (C) → 36aaca7 (E)。CRITICAL 6/6・HIGH 22/22 対応（R1-8 は部分緩和+バックログ）。テスト 106→134。

### Round 2 — 再監査（変更領域中心）実行中
対象 diff: 7c257dc..HEAD。security / code / silent-failure / a11y+frontend の4観点。

#### a11y+frontend（完了）
F1(フォーカスリング)解消確認・エラーバナー/res.ok/コントラスト合格。
| ID | 重大度 | 内容 | 対象 |
|---|---|---|---|
| R2-F1 | HIGH | `load()` 後に `div.closest('section')` を評価 → detached で null → focusSectionHeading 不発、フォーカス body 落ち。load 前に section 参照を確保する | dashboard.html:343,362 |
| R2-F2 | MEDIUM | 回答送信後 hasUnsavedInput() が true のままで load が early-return → 回答済みカード残留。送信成功時に input をクリア | dashboard.html:397,421-423 |
| R2-F3 | LOW | --quiet 未使用変数(dashboard) / アイドルドットのコントラスト / alert の更新順序 | 両HTML |

#### security（完了）
| ID | 重大度 | 内容 | 対象 |
|---|---|---|---|
| R2-S1 | HIGH | _claim_finalization が作業**前**にクレーム確定 → 1回目失敗後の Cloud Tasks リトライが dedup 扱いで永久データロス（成功として記録）。クレームを作業完了後に移すか失敗時ロールバック | main.py:150-168 |
| R2-S2 | HIGH | 共有 ThreadPoolExecutor(4) + .result() タイムアウトなし → 外部呼び出し4件のハングで全セッションの /chat・/converse が停止。result(timeout=) 付与 | chat.py:23-25, prefetch_context/chat_turn |
| R2-S3 | MEDIUM | rate limited ログの client_key にトークン先頭8文字 → ハッシュ化推奨 | rate_limit.py |
| R2-S4 | LOW | x-request-id の無検証伝播（形式バリデーション推奨） / 415 は表明ベース | main.py, background_queue.py |

#### silent-failure（完了）
SF1-SF12 の再発なし（SF6/7/10/12 は MEDIUM/LOW 残存=バックログ）。produce_sentences・_enqueue_or_finalize_turn_background・エラーバナーは新規問題なし。
| ID | 重大度 | 内容 | 対象 |
|---|---|---|---|
| R2-SF1 | HIGH | R2-S1 と同根（claim-then-work）。加えて dedup ログと未完了喪失が同一 INFO で区別不能。2段階クレーム（processing→done）推奨 | main.py:150-167 |
| R2-SF2 | HIGH | マルチインスタンスで tasks キャッシュ stale ミス → complete/delete が None 返しで無ログのまま Google Tasks 未同期。キャッシュミス時の強制リフレッシュ+not-found 時 obs.warning | tasks_client.py:87-139, main.py:71-82 |

#### code-reviewer（完了）
CRITICAL 0。HIGH 1（claim-then-work、R2-S1/SF1 と同一 → 3 agent 一致）。MEDIUM: 共有executor直列化 / list() をロック保持中に実行 / /process・/chat の応答shape変化(resolved dict→raw Task、フロント影響なし確認済) / _record_and_upsert_task_background に open_tasks 未伝搬 / producer.join タイムアウトなし。

#### Round 2 判定
新規 CRITICAL 0・**新規 HIGH 4 系統** → Phase 3 へ戻る（Round 2 修正）:
| ID | 統合元 | 修正 |
|---|---|---|
| R2-A | S1+SF1+CR (3者一致) | finalize claim を2段階化（processing→done、stale 引き継ぎ）+ 失敗時 re-raise で Cloud Tasks リトライ有効化 |
| R2-B | S2+CR-M | 共有 executor に result(timeout) + graceful degradation、直列化緩和、producer.join(timeout) |
| R2-C | SF2+CR-M | キャッシュミス時の強制リフレッシュ二段構え + not-found warning + ロック外 list() |
| R2-D | F1+F2 | dashboard フォーカス参照を load 前に確保 + 回答送信後の input クリア |

### Round 2 修正 — 完了（コミット c29457e）
R2-A〜D 全て実装・検証 PASS。140 passed / ruff 緑。テスト 134→140。

### Round 3 — 再監査（c29457e の diff 限定）実行中
code-reviewer + silent-failure-hunter の2観点。判定: 新規 CRITICAL/HIGH ゼロなら Round 3 として1周目クリーン（Round 2 は HIGH 4 で非クリーン。クリーン2周連続で終了）。

#### silent-failure（完了）: R2-A〜D 解消確認。新規 HIGH 1:
| ID | 重大度 | 内容 | 対象 |
|---|---|---|---|
| R3-1 | HIGH | done マーカー update が非保護 → update のみ失敗＋stale 再クレームで業務ロジック全体が無痕跡で重複実行（履歴二重追記・タスク二重操作）。中間ステータス "effects_applied" 導入か update の保護+ログを推奨 | main.py:289-292 |

#### code-reviewer（完了）: 新規 CRITICAL 1・HIGH 1
| ID | 重大度 | 内容 | 対象 |
|---|---|---|---|
| R3-2 | CRITICAL | 失敗後の Cloud Tasks リトライ（既定 backoff ≪ 120s）が「processing・非stale」で in-progress 扱い → finalize_turn が例外なし return → endpoint 200 → Cloud Tasks がタスク削除 → 永久ロスト（at-least-once が実運用で無効） | main.py:178-206, 334-363 |
| R3-3 | HIGH | stale 再クレームが非トランザクション read-then-update → TOCTOU で二重実行 | main.py:190-200 |

#### Round 3 判定: 非クリーン（CRITICAL 1・HIGH 2）→ Round 3 修正へ
修正設計（司令塔決定）:
1. 失敗時に claim を best-effort で status="failed" にマーク → re-raise（500）。failed は即時再クレーム可（R3-2 解消）
2. _claim_finalization を tri-state 化（claimed/duplicate/in_progress）。in_progress は endpoint が 409 を返し Cloud Tasks に後続リトライさせる（200 でタスクを消さない）
3. done マーカー update は try/except + obs.error で**swallow**（500 にすると効果適用済みターンが再実行され R3-1 の重複を生むため）
4. failed/stale の再クレームは Firestore トランザクションで原子化（R3-3 解消）

### Round 3 修正 — 完了（コミット 922abbc）
tri-state claim + トランザクション reclaim + failed マーク + 409 + done swallow。143 passed / ruff 緑。

### Round 4 — 判定: **クリーン（新規 CRITICAL/HIGH ゼロ）** 1周目
状態機械は仕様どおり（トランザクション順序・ログ位置・例外順序も確認済み）。MEDIUM 3（failed マーカー二重障害時は stale 窓待ちに劣化 / 409 の有界性がキュー設定依存 / fake transaction は排他性そのものを未検証）・LOW 2 → バックログへ。

### Round 5 — 判定: **クリーン（新規 CRITICAL/HIGH なし）**
finalize 状態機械の4経路・/converse producer/consumer・フロント fetch 経路すべて計装/エラー処理の網羅を確認。**Round 4+5 で 2 周連続クリーン成立 → ループ終了。**

---

## Phase 5 — クローズアウト（2026-07-12）

### 最終状態
- テスト: **143 passed**（開始時 106）/ ruff 全パス / 各コミット時点でテスト緑を確認済み（機能非破壊）
- コミット: 7ad7575 → ad7829e → 59eabab → 36aaca7 → c29457e → 922abbc（6コミット、未 push）

### ビフォー/アフター（観点別）
| 観点 | Before | After |
|---|---|---|
| セキュリティ | finalize-turn レート制限なし・履歴汚染注入可・冪等性なし・セキュリティヘッダなし | レート制限・turn_id 冪等状態機械・X-Frame-Options/nosniff/Referrer-Policy・audio 415 検証 |
| 可観測性 | /tasks/*・record_and_resolve・401/429 が ERROR アラート圏外、Cloud Tasks 相関断絶 | 全経路 obs 計装、X-Request-Id 伝播、finalize 経路/リトライ回数/dedup 可視化 |
| 信頼性 | 二重確定・claim-then-work データロス・executor 枯渇・キャッシュ stale 無音失敗 | at-least-once×効果非重複の状態機械（トランザクション排他）、timeout+degradation、二段キャッシュ+警告 |
| パフォーマンス | Gemini×TTS 完全直列・Google Tasks N+1・クライアント毎回生成 | パイプライン化（文間ギャップ短縮）・TTL キャッシュ・シングルトン統一・二重再生ガード |
| フロント/a11y | 偽成功アナウンス・ボタン恒久死・フォーカスリング 2.3:1・Linear 実ブランド色 | res.ok+エラーバナー+フォーカス管理・9.4:1・独自色 #6E5BD6・high-priority 可視化 |
| テスト | 106（質問ループ・/converse 失敗系ゼロ） | 143（状態機械・失敗系・冪等性・キャッシュを含む） |

### バックログ（MEDIUM/LOW — 今回対象外、勝手に膨らませない）
**要手動/インフラ判断:**
- SEC2 完全対策: /internal/finalize-turn を Cloud Tasks OIDC + ingress 制限へ分離（現在は turn_id 冪等化+レート制限で緩和済み）
- Cloud Tasks キューの max_retry_duration/max_attempts 設定（409 リトライの有界性を YUI_FINALIZE_STALE_SEC=120s より長く保証する）
- PA6: gemini-3.5-flash モデルIDの実在を gcloud/コンソールで確認しコメント化
- PA7/C8/H15: 返答テキスト非表示の意思決定を audit_summary 上で正式クローズ（字幕トグル折衷案含む）
- P2: Cloud TTS Streaming の 1ストリーム複数 input 可否を API 仕様で確認 → 可なら1ターン1ストリーム化
- P9: 本番トレースサンプリング率（YUI_TRACE_SAMPLE）の調整判断

**コード改善（次回ラウンド候補）:**
- PA5: /health deep チェック（カナリア判定の強化）
- SF6: Google Tasks API 呼び出しの call_with_retry / SF7: agent_loop/autonomous_review の failed カウント集約 / SF10: speakAndWait の showError / SF11: STT/TTS retry / SF12: degraded フラグ
- R2-S3: rate limited ログの client_key ハッシュ化 / R2-S4: x-request-id 形式バリデーション
- R4-M: failed マーカー二重障害時の stale 窓依存（現状は劣化フォールバックとして許容）/ fake transaction の排他性検証 / timeout 後 future の例外回収
- O8/O9: /converse の Gemini/TTS 区間計測・prefetch 内訳・ログへの trace_id 付与
- CR-M: /process・/chat 応答 shape の文書化、_record_and_upsert_task_background への open_tasks 伝搬
- A3/A4 残り・D6-D9 の一部（縦リズム・エレベーション等のデザイン磨き込み）
- obs severity 基準の文書化 / CHANGELOG 導入 / test_extraction.py

### 総括
CRITICAL 7 件（R1: 6 + R3: 1）・HIGH 24 件（R1: 22 + R2: 4 + R3: 2、統合後）を 3 ラウンドの修正で全て解消。Round 2・3 の指摘はすべて Round 1・2 の修正自身が持ち込んだ回帰であり、loop-until-dry が設計どおり機能した。機能破壊ゼロ（全コミットでテスト緑維持）。


## findings 表（Round 1 集約中）

### silent-failure-hunter（完了）
| ID | 重大度 | 内容 | 対象 |
|---|---|---|---|
| SF1 | CRITICAL | /converse 正常系の `await context_future` が try/except 外 → prefetch 失敗で obs.error なしの素500 | main.py:425 |
| SF2 | CRITICAL | dashboard の complete/dismiss/answer が res.ok 未確認で成功アナウンス＋ボタン恒久 disabled | static/dashboard.html:301-347 |
| SF3 | HIGH | embedding 失敗ログに例外詳細なし・WARNING 止まり（重複タスク生成の正確性劣化なのに不可視） | memory_store.py:180-186 |
| SF4 | HIGH | Cloud Tasks enqueue 失敗が恒久的設定ミス(YUI_APP_TOKEN KeyError)含め全て WARNING。in-process フォールバックは非永続でターン喪失が無痕跡 | background_queue.py:56-63, main.py:503-504 |
| SF5 | MEDIUM | 空 reply でターン丸ごと無記録ドロップ（finalize_turn 不実行、ログなし） | main.py:502-505 |
| SF6 | MEDIUM | Google Tasks API 呼び出しに retry なし → Firestore と Google Tasks の state drift | tasks_client.py |
| SF7 | MEDIUM | agent_loop/autonomous_review の per-item 失敗がジョブサマリに未集約（failed カウントなし） | agent_loop.py, autonomous_review.py |
| SF8 | MEDIUM | dashboard load() にエラー処理ゼロ → 15s ポーリングが無言で死に続ける | static/dashboard.html:367-407 |
| SF9 | MEDIUM | cosine_similarity の次元不一致が無ログで 0.0（モデル変更後の恒久劣化が不可視） | embeddings.py:22-33 |
| SF10 | LOW | speakAndWait の TTS 失敗が console のみ（showError 不使用） | static/index.html:494-519 |
| SF11 | LOW | STT/TTS に call_with_retry なし（Gemini と非対称） | speech_to_text.py, tts.py |
| SF12 | LOW | /process・/chat の意図的degradationに機械可読 degraded フラグなし | main.py:192-197,227-243 |

### 2aio-project-auditor（完了）
前回 CRITICAL/HIGH の回帰確認: C1/C3/C4/H1/H2/H3/H6/H9/H11/H13/C7/H14/README ほぼ全て修正済み・回帰なし。
| ID | 重大度 | 内容 | 対象 |
|---|---|---|---|
| PA1 | CRITICAL | **C5 未修正**: Google Tasks N+1（`_find_matching_task` が毎回全件 list + 線形一致）が audit_summary で「対応済み」誤記のまま残存 | tasks_client.py:77-132 |
| PA2 | HIGH | セキュリティヘッダ・CORS・Content-Type 検証ゼロ（前回MEDIUM→格上げ。X-Frame-Options/nosniff/audio型検証） | main.py 全体 |
| PA3 | HIGH | /internal/finalize-turn にレート制限なし | main.py:166 |
| PA4 | HIGH | calendar_client の service 毎回再構築（C6 の未収束） | calendar_client.py:11-12 |
| PA5 | MEDIUM | /health がシャロー（カナリア判定が Firestore/Vertex 障害をすり抜け） | main.py:161-163 |
| PA6 | MEDIUM | gemini-3.5-flash モデルIDの実在検証コメントなし | clients.py:12 |
| PA7 | MEDIUM | C8/H15 の意思決定が記録上宙ぶらりん（audit_summary 更新要） | docs/記録 |
| PA8 | LOW | test_extraction.py 不在 / obs severity基準未文書化 / CHANGELOG なし 等 | — |

### security-reviewer（完了）
C1/C2/H6/H7 回帰なし。XSS シンクなし。
| ID | 重大度 | 内容 | 対象 |
|---|---|---|---|
| SEC1 | HIGH | /internal/finalize-turn レート制限なし → Gemini コストDoS（PA3 と同一） | main.py:166 |
| SEC2 | HIGH | /internal/finalize-turn が任意 reply を無検証で role=model として履歴永続化 → 履歴汚染型プロンプトインジェクション。Cloud Tasks OIDC 分離推奨 | main.py:79-81,135-138, chat.py:136-160,236-239 |

### a11y-architect（完了）
前回 H14/LOW 群はほぼ解消確認。
| ID | 重大度 | 内容 | 対象 |
|---|---|---|---|
| A1 | HIGH | :focus-visible が半透明で実効コントラスト ~2.3:1（WCAG 2.4.11/1.4.11） | index.html:142, dashboard.html:166 |
| A2 | MEDIUM | --quiet #62666D の本文コントラスト 3.4:1 未達 | index.html:43,155 |
| A3 | MEDIUM | ターゲットサイズ 24px 未満（#dashLink, 戻りリンク, complete/dismiss） | 両HTML |
| A4 | MEDIUM | 完了/取消後のフォーカス喪失（2.4.3） | dashboard.html:301-320 |
| A5 | MEDIUM | 返答テキストの SR 専用ライブリージョン代替案（ユーザー決定尊重の折衷） | index.html |
| A6-A10 | LOW | role=list 直下の empty div / badge aria-label が言及回数を隠す / ❓絵文字読み上げ / nav なし / off時 orb 無反応 | 両HTML |

### 2aio-design-reviewer（完了）
| ID | 重大度 | 内容 | 対象 |
|---|---|---|---|
| D1 | CRITICAL | アクセント #5E6AD2 が Linear 実ブランドカラーとビット一致（Linearクローン判定・法的リスク） | index.html:20, dashboard.html:21 |
| D2 | HIGH | .card.high-priority の border-left 4px が色未指定で実質不可視（機能死） | dashboard.html:107 |
| D3 | HIGH | .complete-button に hover なし（dismiss と非対称） | dashboard.html:139-150 |
| D4 | HIGH | --quiet コントラスト AA 未達（A2 と同一） | index.html:43 |
| D5 | HIGH | セクション h2 の色が ask のみ（progress/done 未展開） | dashboard.html:68 |
| D6 | MEDIUM | index の縦リズム完全均一 gap:22px（前回未解消） | index.html:40,48 |
| D7 | MEDIUM | priority=2 色が --done と同一緑で意味衝突 | dashboard.html:209,26 |
| D8 | MEDIUM | カードにエレベーションなし（header blur と不整合） | dashboard.html:69-76 |
| D9 | MEDIUM | エラーと通常ヒントが同一スタイル（#hint 共用） | index.html:110,313-319 |
| D10 | LOW | ❓絵文字残存 / トグル文言非対称 | 両HTML |

### pr-test-analyzer（完了）
| ID | 重大度 | 内容 | 対象 |
|---|---|---|---|
| T1 | CRITICAL相当 | answer_question（質問ループ状態遷移）のテストゼロ | agent_loop.py:201-220 |
| T2 | HIGH | run_agent_loop の research/draft/monitor/重複質問抑止 分岐が未テスト | agent_loop.py:120-198 |
| T3 | HIGH | /converse ミッドストリーム失敗（部分チャンク後の raise、finalize スキップ=ターン喪失）未テスト | main.py:483-501 |
| T4 | HIGH | /converse の STT 失敗分岐・413 オーバーサイズ未テスト | main.py:371-404 |
| T5 | MEDIUM | 意味的再言及の閾値「未満」側・不正env・複数候補が未テスト | memory_store.py:191-210 |
| T6 | MEDIUM | record_and_resolve テストが where_calls を未検証（モック過剰） | tests/test_memory_store.py |
| T7 | MEDIUM | test_embeddings.py 不在（embed_text の呼び出し形・env パース） | embeddings.py |
| T8 | MEDIUM | finalize_turn の Cloud Tasks リトライ二重実行（冪等性ガードなし・重複タスク生成リスク）未テスト/未実装 | main.py:166-180 |
| T9 | LOW | tts 途中raise / sentence_split 境界 / _sample_ratio 不正値 未テスト | 各所 |

### 2aio-observability（完了）
| ID | 重大度 | 内容 | 対象 |
|---|---|---|---|
| O1 | CRITICAL | /tasks/{id}/answer・complete・DELETE に try/except+obs.error なし → ERROR アラート素通り | main.py:573-596 |
| O2 | CRITICAL | /process・/chat の record_and_resolve 呼び出しが try/except 外（中核機能の記録失敗が不可視） | main.py:199-202,247-250 |
| O3 | HIGH | 401/429 が一切ログされない（auth.py に obs ゼロ） | auth.py:60-64, rate_limit.py:51-66 |
| O4 | HIGH | Cloud Tasks 経由で request_id/traceparent 相関断絶 | background_queue.py:37-53, main.py:145-152 |
| O5 | HIGH | finalize 経路(cloud_tasks/fallback)とリトライ回数が完了ログに出ない | main.py:503-517 |
| O6 | HIGH | embed_text 計装皆無 + except の detail 欠落（SF3 と同一） | embeddings.py:13-19, memory_store.py:181-186 |
| O7 | HIGH | finalize_turn 内ループに per-item try/except なし・title 不記録（1件失敗で残り全滅） | main.py:79-132 |
| O8 | MEDIUM | /converse の Gemini/TTS 区間・prefetch 内訳の計測欠落、フォールバック回数カウンタなし | main.py:406-517, chat.py:172-200 |
| O9 | MEDIUM | ログに trace_id/span_id なし（Cloud Trace→ログ遷移不能） | obs.py, tracing.py |
| O10 | MEDIUM | tasks_client に duration/task_count 計装なし | tasks_client.py:86-132 |
| O11 | LOW | env パース失敗の無音フォールバック | memory_store.py:18-23 ほか |

### performance-optimizer（完了）
| ID | 重大度 | 内容 | 対象 |
|---|---|---|---|
| P1 | CRITICAL | Gemini ストリーム消費と TTS 合成が完全直列（文N合成中は文N+1生成が停止）→ パイプライン化で複数文の再生ギャップ大幅短縮 | main.py:483-493 |
| P2 | HIGH | 文ごとに TTS bidi ストリームを張り直し（API仕様で1ストリーム複数input可なら統合） | tts.py:34-62 |
| P3 | HIGH | stream_synthesize 部分成功後のフォールバックで同一文が二重再生 | main.py:439-479 |
| P4 | HIGH | prefetch_context/chat_turn が毎回 ThreadPoolExecutor 新規生成（入れ子スレッドプール） | chat.py:174,212 |
| P5 | MEDIUM | record_and_resolve が finalize 内で find_open_tasks を N 回再フェッチ（N+1） | memory_store.py:187, main.py:88-94 |
| P6 | MEDIUM | find_open_tasks が done も取得後 Python フィルタ（limit 枠を浪費） | memory_store.py:71-86 |
| P7 | MEDIUM | enqueue_finalize_turn が done イベント送出前に同期ブロッキング | main.py:502-505 |
| P8 | MEDIUM | tts._get_client がロックなし（clients.py と非対称） | tts.py:9-16 |
| P9 | MEDIUM | 本番トレースサンプリング率デフォルト100% | tracing.py:20-26 |
| P10 | LOW | env 再読込 / _MIN_SPEECH_CHARS チューニング | embeddings.py:36-38 ほか |

### python-reviewer（完了）ruff は全パス
| ID | 重大度 | 内容 | 対象 |
|---|---|---|---|
| PY1 | HIGH | 413 分岐の await context_future が無ログ握りつぶし（兄弟分岐と非対称） | main.py:371-376 |
| PY2 | HIGH | record_and_resolve の再言及ロジックが _resolve_remention と手書き重複（ドリフト温床） | memory_store.py:138-178 vs 26-51 |
| PY3 | HIGH | tts._get_client スレッド非安全（P8 と同一） | tts.py:9-16 |
| PY4 | HIGH | setup_tracing(app) / stream_synthesize / stream_reply / fetcher 引数の型注釈欠落 | tracing.py:34, tts.py:34, chat.py:203-309 |
| PY5 | MEDIUM | asyncio.get_event_loop() 非推奨（get_running_loop へ） | main.py:368 |
| PY6 | MEDIUM | background_queue の KeyError と transient を同一 except で混同（SF4 と同一） | background_queue.py:34-63 |
| PY7 | MEDIUM | embed_text に call_with_retry なし（SF11 系） | embeddings.py:13-19 |
| PY8 | LOW | for data in [doc.to_dict()] の難読イディオム / span 型 / main.py 内部ジェネレータ型 | memory_store.py:98-106 ほか |
