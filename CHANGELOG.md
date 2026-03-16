# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルは、リポジトリ内のソースコードから推測される機能追加・設計方針・修正点を基に作成した初期の変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-03-16
初回リリース。日本株自動売買プラットフォームの基盤機能を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - kabusys パッケージの公開 API を定義（__version__ = 0.1.0、data/strategy/execution/monitoring をエクスポート）。
- 環境設定管理（kabusys.config）
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロード無効化可能。
  - .env パーサーはコメント行、export プレフィックス、シングル/ダブルクォート、エスケープシーケンス、インラインコメントを考慮。
  - Settings クラスでアプリケーション設定をプロパティとして提供（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、データベースパス、環境/ログレベルチェックなど）。
  - 必須環境変数未設定時に明確なエラーメッセージを返す _require() を実装。
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日次株価（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得用のクライアントを実装。
  - レート制限（120 req/min）を守る固定間隔スロットリング _RateLimiter を実装。
  - リトライ機構（指数バックオフ、最大 3 回）を実装。対象ステータス: 408/429/5xx。429 時は Retry-After ヘッダを優先。
  - 401 応答時にリフレッシュトークンで自動的に id_token を更新して 1 回リトライ（無限再帰を回避）。
  - ページネーション対応（pagination_key の追跡）とモジュールレベルでの id_token キャッシュを実装。
  - 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias を防ぐ設計。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）は冪等（ON CONFLICT DO UPDATE）で実装。
  - 型安全な変換ユーティリティ _to_float / _to_int を提供（空値・不正値ハンドリング、"1.0" 等の float 文字列の安全な int 変換）。
- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の多層スキーマを DDL として定義。
  - raw_prices, raw_financials, raw_news, raw_executions を含む Raw 層。
  - prices_daily, market_calendar, fundamentals 等の Processed 層。
  - features, ai_scores 等の Feature 層。
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution 層。
  - パフォーマンス向上のためのインデックス群を定義（銘柄×日付、ステータス検索、FK ジョイン用等）。
  - init_schema(db_path) でディレクトリ作成・DDL 実行を行い接続を返す（冪等）。get_connection() も提供。
- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL 実行のための総合入口 run_daily_etl() を実装。
  - 処理フロー: 市場カレンダー取得（先読み）→ 株価差分更新（バックフィル）→ 財務差分更新 → 品質チェック（オプション）。
  - 差分更新ロジック: DB の最終取得日からの差分取得、自動算出される date_from、バックフィル日数（デフォルト 3 日）による後出し修正吸収。
  - カレンダー先読みデフォルト 90 日（_CALENDAR_LOOKAHEAD_DAYS）。
  - 取得済みの pagination_key 重複防止、取得数/保存数のログ出力。
  - ETL 実行結果を ETLResult dataclass で返却（品質問題やエラーの収集、to_dict で可視化可能）。
- 監査ログ（kabusys.data.audit）
  - シグナル → 発注要求 → 約定 のトレーサビリティを担う監査テーブル群を実装（signal_events, order_requests, executions）。
  - UUID ベースの冪等キー（order_request_id、broker_execution_id など）とステータス設計。
  - すべての TIMESTAMP を UTC で保存するための初期化処理（SET TimeZone='UTC'）。
  - init_audit_schema(conn) / init_audit_db(db_path) により監査用テーブルとインデックスを冪等で初期化。
- データ品質チェック（kabusys.data.quality）
  - QualityIssue dataclass と複数のチェック関数を実装。
  - 実装済みチェック:
    - check_missing_data: raw_prices の OHLC 欠損検出（重要度: error）。
    - check_spike: 前日比のスパイク検出（デフォルト閾値 50%）。LAG を用いた SQL 実装でサンプルと総数を取得。
  - チェックは Fail-Fast ではなく全問題を収集して返却する設計。
  - DuckDB 上でパラメータバインド（?）を用いた安全な SQL 実行。
- ロギング
  - 各モジュールで logger を使用して主要イベント（取得件数、保存件数、リトライ警告、欠損やスパイクの検出など）を出力。

### Changed
- 初期リリースのため、既存ライブラリからの大きな変更履歴はありませんが、設計方針として以下を明記:
  - 冪等性重視（DB 書き込みは ON CONFLICT DO UPDATE）とトレーサビリティ重視（created_at/updated_at の保存、UTC 時刻）。
  - エラー耐性: 各 ETL ステップは個別に例外を捕捉し、他ステップへ影響を与えない形で処理を継続。
  - テスト容易性: id_token を注入可能、.env 自動ロードを無効化するフラグを提供。

### Fixed
- 初版の実装における明示的なバグ修正履歴はなし（初回リリース）。

### Security
- 環境変数保護: os.environ のキーを protected として .env による上書きを制御。必須値の未設定時は ValueError を投げることで誤った運用を防止。

---

注記:
- 本 CHANGELOG はコードベースの実装内容から推測して作成しています。実際のリリースノート作成時は、コミットメッセージや変更履歴（git log）を参照し、リリース日やバージョン、責任者・影響範囲などを追記してください。