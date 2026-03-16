# Changelog

すべての注目すべき変更を記録します。本ドキュメントは「Keep a Changelog」準拠の形式で記載しています。

## [0.1.0] - 2026-03-16

### Added
- 初回リリース: KabuSys — 日本株自動売買システムのコアライブラリを追加。
- パッケージ情報
  - kabusys.__version__ = "0.1.0" を設定。
  - パッケージの公開 API として data, strategy, execution, monitoring を定義（strategy/execution のパッケージはプレースホルダを含む）。
- 設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装。
  - プロジェクトルート判定ロジック（.git または pyproject.toml 基準）により CWD に依存しない自動ロードを実現。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート（テスト用）。
  - .env パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント規則を適切に扱う。
  - 環境変数保護機構（既存 OS 環境変数は .env で上書きされない / .env.local は上書き可）。
  - Settings クラスを提供し、必須変数取得（_require）、env / log_level の妥当性チェック、各種設定プロパティ（J-Quants トークン、kabu API、Slack、DB パスなど）を公開。
- J-Quants クライアント (kabusys.data.jquants_client)
  - API クライアントを実装（/token/auth_refresh, /prices/daily_quotes, /fins/statements, /markets/trading_calendar）。
  - ページネーション対応で全ページを取得する fetch_* 関数を提供（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - API レート制限対応（固定間隔スロットリング: 120 req/min）を実装（内部 RateLimiter）。
  - 再試行ロジックを実装（指数バックオフ、最大 3 回、HTTP 408/429/5xx を対象）。429 の場合は Retry-After を優先。
  - 401 受信時は自動的にリフレッシュトークンで id_token を再取得して 1 回リトライ（無限再帰回避）。
  - id_token のモジュールレベルキャッシュを導入（ページネーション間でトークン共有）。
  - データ取得時に fetched_at を UTC ISO8601 形式で記録することで look-ahead bias のトレースを可能に。
  - DuckDB への保存関数を提供（save_daily_quotes, save_financial_statements, save_market_calendar）。いずれも冪等性を担保する ON CONFLICT DO UPDATE を採用。
  - 値変換ユーティリティを提供（_to_float, _to_int）で空値・変換エラーを安全に処理。
- データスキーマ (kabusys.data.schema)
  - DuckDB 用の包括的なスキーマ定義を実装（Raw / Processed / Feature / Execution 層）。
  - raw_prices, raw_financials, raw_news, raw_executions などの Raw テーブル。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブル。
  - features, ai_scores 等の Feature テーブル。
  - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等の Execution テーブル。
  - 頻出クエリを想定したインデックスを作成。
  - init_schema(db_path) によりディレクトリ自動作成とテーブルの冪等初期化を提供。get_connection() で既存 DB に接続可能。
- ETL パイプライン (kabusys.data.pipeline)
  - 日次 ETL の設計と実装（run_daily_etl をメインエントリポイントとして提供）。
  - 差分更新ロジック: DB の最終取得日を元に未取得範囲を自動算出し、backfill_days により数日前から再取得して API の後出し修正に対応（デフォルト backfill_days=3）。
  - カレンダーは先読み（デフォルト 90 日）で取得し、営業日調整に利用。
  - 個別ジョブ実装: run_calendar_etl, run_prices_etl, run_financials_etl（各ジョブは差分取得・保存を実施）。
  - ETL 実行結果を表す ETLResult データクラスを導入（収集した品質問題・エラーを格納）。
  - 各ステップは独立してエラーハンドリングされ、1 ステップ失敗でも他ステップは継続（エラーは ETLResult に収集）。
  - 品質チェック連携（quality モジュール）をオプションで実行可能。
- 品質チェック (kabusys.data.quality)
  - データ品質チェック機能を実装（欠損データ、スパイク、重複、日付不整合などの検出を想定）。
  - QualityIssue データクラスを定義（check_name, table, severity, detail, rows）。
  - check_missing_data: raw_prices の OHLC 欠損検出（サンプル行取得と件数ログ）。欠損は重大度 error。
  - check_spike: 前日比スパイク検出（LAG を用いた SQL 実装、デフォルト閾値 50%）。
  - DuckDB 上の SQL をパラメータバインドで安全に実行する設計。
- 監査ログ / トレーサビリティ (kabusys.data.audit)
  - シグナル→発注→約定の完全トレーサビリティを目的とした監査テーブル群を実装（signal_events, order_requests, executions）。
  - order_request_id を冪等キーとして扱い、再送時の二重発注防止を想定。
  - すべての TIMESTAMP は UTC（初期化時に SET TimeZone='UTC' を実行）。
  - 詳細なチェック制約、FK、ステータス列を定義（order_requests の order_type に応じた price チェックなど）。
  - 監査用インデックス群を作成し、検索・ジョイン効率を向上。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供。
- ロギングと診断情報
  - 各主要処理（fetch/save/etl/run）で info / warning / error ログを出力。
  - API エラー・再試行やスキップ行数などの診断情報をログに残す。

### Changed
- 初回リリースのため該当なし（新規実装）。

### Fixed
- 初回リリースのため該当なし。

### Security
- API リフレッシュトークンは Settings を通して環境変数で管理する設計（ソースコード中にハードコーディングしない前提）。
- .env 自動読み込みでも既存 OS 環境変数を保護する仕組みを導入。

### Notes / Known limitations
- strategy/ execution パッケージはプレースホルダ（__init__.py のみ）として存在し、戦略本体や実際のブローカー連携は未実装。
- RateLimiter は同期的に time.sleep を用いる実装のため、並列化／高負荷環境では非同期実装やトークンバケット等の検討が必要。
- id_token のキャッシュはモジュールレベルの簡易実装。分散プロセスやマルチスレッド環境での共有を考慮する場合は外部ストア等の導入を検討。
- DuckDB の ON CONFLICT や INDEX の挙動はバージョン依存があるため、運用環境の DuckDB バージョンでの検証が必要。
- quality モジュールは主要チェックの骨格を提供。追加のチェックや閾値調整、通知連携などは今後の改善点。
- ネットワークタイムアウトは urllib のデフォルトで 30 秒に設定。要件に応じて調整の検討を推奨。

---

このリリースは初期の基盤実装を提供するもので、データ取得・保存・品質管理・監査ログの主要な機能をカバーしています。今後のバージョンでは戦略実装、ブローカー発注連携、非同期化・性能改善、追加の品質チェックやモニタリング機能を計画しています。