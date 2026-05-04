# Core機能と拡張機能（AI/LINE/UI）の疎結合化（Issue #232 — 実装完了）

本ドキュメントは、KabuSysにおいて「拡張機能（AIセンチメント、LINE通知、運用UI）が停止・未設定であっても、Core機能（自動売買）が絶対に影響を受けないアーキテクチャ」を実現するための改修記録です。

> **ステータス**: Issue #232 / PR #241 にてすべての主要タスクが実装・マージ済み（2026-05-04）。

---

## 1. Feature Toggle（機能フラグ）の導入 ✅

- [x] `src/kabusys/config.py` の修正
  - `_parse_bool_env()` ヘルパーを実装（許容リスト方式: `"1"/"true"/"yes"/"on"` のみ `True`）
  - 以下のフラグを追加（デフォルト `False` = 安全側）
    - `ENABLE_AI_SENTIMENT` → `Settings.enable_ai_sentiment`
    - `LINE_NOTIFY_ENABLED` → `Settings.line_notify_enabled`（当初 `ENABLE_LINE_NOTIFY` と命名予定だったが、既存 `LineNotifier` との整合を取り `LINE_NOTIFY_ENABLED` に変更）
- [x] `.env.example` の修正
  - Feature Toggle セクションを追加し、`ENABLE_AI_SENTIMENT=false` / `LINE_NOTIFY_ENABLED=false` のサンプルを記載

## 2. AIモジュールのフェイルセーフ（欠損値へのフォールバック） ✅

- [x] `src/kabusys/ai/news_nlp.py` の修正
  - 関数先頭で `Settings().enable_ai_sentiment` をチェックし、`False` の場合は INFO ログを出力して即座に `0` を返す
  - API キー未設定時も `ValueError` を投げず `0` を返す（WARNING ログ付き）
- [x] `src/kabusys/strategy/signal_generator.py` の確認・強化
  - `ai_enabled = Settings().enable_ai_sentiment` をループ外で1回だけ評価
  - AIスコアが欠損（`None`）かつ `ai_enabled=True` の場合のみ WARNING を出力（AI 無効時はログを出さない）

## 3. LINE通知の疎結合化 ✅（アーキテクチャ変更: Null Object パターン採用）

当初の設計案（`notification_events` テーブル + `notifier_worker.py` によるイベント駆動方式）から、より単純な **Null Object パターン** に変更した。

- [x] `src/kabusys/operations/notifier.py` に以下を実装
  - `NullNotifier`: `send()` が常に `False` を返すだけの安全なノップ実装
  - `build_notifier(settings)`: `LINE_NOTIFY_ENABLED=false` またはトークン/ユーザーID 未設定時に `NullNotifier` を返すファクトリ関数
- Core コード（`run_execution.py` 等）は `build_notifier()` が返すオブジェクトの `.send()` を呼ぶだけでよく、LINE API の有効/無効を意識しない設計を実現

> **変更理由**: イベントドリブン方式は今後の拡張には適しているが、現フェーズでは同期的な Null Object パターンで十分。`notifier_worker.py` は別 Issue で検討。

## 4. UI設定ファイルのRead-Only制約と安全な初期値（別 Issue に分離）

`strategy_config.json` 未存在時の安全なフォールバックは別 Issue として分離。Issue #232 のスコープ外。
