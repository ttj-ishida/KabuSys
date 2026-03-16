CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に準拠しています。

[Unreleased]: https://example.com/kabusys/compare/main...HEAD

[0.1.0] - 2026-03-16
--------------------

初回リリース — 日本株自動売買システムのコアライブラリを実装しました。以下はコードベースから推測される主な機能・設計上のポイントです。

### Added
- パッケージ全体
  - kabusys パッケージの初期実装。公開モジュール: data, strategy, execution, monitoring（strategy/execution/monitoringはパッケージ初期化のみ）。
  - バージョン: 0.1.0

- 環境・設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env のパース機能強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱いを考慮。
    - コメントや無効行を無視する堅牢な実装。
  - Settings クラスを提供（J-Quants / kabu API / Slack / DB パス / 実行環境 / ログレベル等のプロパティ、必須キーは未設定時に明示的な例外を送出）。
  - KABUSYS_ENV と LOG_LEVEL の値検証（事前定義された有効値のみ許可）。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API クライアントの実装（価格日足、財務データ、JPXマーケットカレンダーの取得）。
  - レート制御: 固定間隔スロットリングによる 120 req/min 制限（RateLimiter 実装）。
  - 再試行ロジック: 指数バックオフ、最大 3 回リトライ、対象ステータス(408, 429, 5xx)を考慮。429 の場合は Retry-After ヘッダ優先。
  - 認証トークン管理:
    - refresh_token からの id_token 取得関数 (get_id_token)。
    - 401 受信時は id_token を自動リフレッシュして 1 回リトライ（無限再帰防止）。
    - モジュールレベルのトークンキャッシュをページネーション間で共有。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar）。
  - DuckDB へ保存する save_* 関数（save_daily_quotes、save_financial_statements、save_market_calendar）:
    - 冪等性を保証するため ON CONFLICT DO UPDATE を使用。
    - fetched_at は UTC タイムスタンプで記録（ISO 8601, Z 表記）。
  - 入出力ユーティリティ: _to_float / _to_int（不正値・欠損に対する頑健な変換処理）。

- データベーススキーマ（kabusys.data.schema）
  - DuckDB 用スキーマ定義をレイヤー別に実装（Raw / Processed / Feature / Execution）。
  - 多数のテーブルDDLを定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance など）。
  - 型制約、CHECK 制約、主キー・外部キーを適切に設定。
  - 検索性能を考慮したインデックス定義群（例: code×date の検索、ステータスによるスキャン）。
  - init_schema(db_path) によりディレクトリ自動作成・DDL 実行・インデックス作成を行う API と get_connection を提供。

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL の実装（run_daily_etl）:
    - 市場カレンダー取得 → 営業日調整 → 株価日足差分ETL → 財務データ差分ETL → 品質チェック の順で実行。
    - 各ステップは独立して例外処理され、片方が失敗しても他は継続（エラーは結果オブジェクトへ集約）。
    - 差分更新ロジック: DB の最終取得日をもとに未取得分のみを取得、バックフィル日数(backfill_days) により過去数日分を再取得して API の後出し修正を吸収。
    - カレンダーは先読み (lookahead_days) して将来の営業情報を確保。
  - ETLResult データクラスにより取得/保存件数、品質問題、エラーを集約。品質問題の有無・重大度判定用ヘルパを提供。
  - get_last_price_date / get_last_financial_date / get_last_calendar_date 等のユーティリティを提供。
  - _adjust_to_trading_day による非営業日の調整（market_calendar によるフォールバックを実装）。

- 品質チェック（kabusys.data.quality）
  - QualityIssue データクラスを定義（check_name, table, severity, detail, rows）。
  - 実装済みチェック:
    - 欠損データ検出 (check_missing_data): raw_prices の OHLC 欄の欠損を検出（volume は除外）。
    - スパイク検出 (check_spike): LAG ウィンドウで前日比を算出し、閾値超の変動を検出（デフォルト閾値 50%）。SQL ベースで効率的に処理。
  - 各チェックは Fail-Fast ではなくすべての問題を収集して呼び出し元に返す設計。

- 監査ログ（kabusys.data.audit）
  - シグナル → 発注要求 → 約定 のトレーサビリティを保証する監査用スキーマを実装（signal_events, order_requests, executions）。
  - order_request_id を冪等キーとして二重発注防止を想定。
  - すべての TIMESTAMP を UTC で保存するよう init_audit_schema が TimeZone='UTC' を設定。
  - 各種制約・インデックスを設定し、init_audit_db(db_path) で監査専用 DB を初期化できる。

- その他ユーティリティ・設計上の配慮
  - HTTP エラー・ネットワークエラーに対する詳細なログと再試行メッセージ（Retry-After ヘッダ優先）。
  - DuckDB への接続処理はファイルパスの親ディレクトリを自動作成してくれるため、初期化が容易。
  - SQL 実行はパラメーターバインド（?）を使用するよう配慮（インジェクション対策）。
  - ロギングを随所に配置し、処理の可観測性を高める設計。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- 初回リリースのため該当なし。

Notes / 利用上の注意
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings から参照され、未設定時は例外となります。
- DB 初期化:
  - 最初に data.schema.init_schema() を呼んで DuckDB スキーマを作成してください（:memory: の利用も可能）。
  - 監査ログを別 DB に保持したい場合は data.audit.init_audit_db() を利用してください。
- 自動 .env 読み込み:
  - パッケージはプロジェクトルートを探索して .env/.env.local を自動読み込みします。テストなどで自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ETL の堅牢性:
  - run_daily_etl は各ステップごとに例外を捕捉して結果にエラーを記録します。呼び出し元は ETLResult を参照して必要な対処（アラート送出、再試行等）を行ってください。

今後の改善案（参考）
- strategy / execution / monitoring モジュールの具体実装（現状はパッケージプレースホルダ）。
- API クライアントのテストフック（HTTP レスポンスのモック注入）強化。
- 追加の品質チェック（重複チェック、将来日付検知の厳格化など）。
- データ保存時のバルク処理最適化（大量データ時のパフォーマンス検証）。

以上。