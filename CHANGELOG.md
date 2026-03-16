# Changelog

すべての重要な変更点は Keep a Changelog の形式に従って記録します。初回公開リリースおよび主要な追加機能・設計方針を以下にまとめます。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-16

初回リリース — 日本株自動売買プラットフォームのコアライブラリを実装しました。主にデータ取得・保存、ETLパイプライン、監査ログ、設定管理、基本スキーマ等を含みます。

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を設定（src/kabusys/__init__.py）。
  - モジュール公開: data, strategy, execution, monitoring を __all__ に追加。

- 環境変数・設定管理（src/kabusys/config.py）
  - Settings クラスを導入し、環境変数からアプリ設定を取得（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
  - .env 自動読み込み機構を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサ: export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いをサポート。
  - 設定値検証: KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）の検証プロパティを実装。
  - デフォルト DB パス: DUCKDB_PATH、SQLITE_PATH に対するデフォルト設定を提供。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得するクライアントを実装。
  - レート制限保護: 固定間隔スロットリングに基づく RateLimiter（120 req/min）。
  - リトライロジック: 指数バックオフ（base 2.0）、最大 3 回、対象ステータス (408, 429, 5xx)。
  - 401 Unauthorized 受信時の自動トークンリフレッシュ（1 回だけリトライ）。
  - ID トークンのモジュールレベルキャッシュを実装（ページネーション間で共有）。
  - ページネーション対応（pagination_key を用いた全ページ取得）。
  - データ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
  - DuckDB 保存関数（冪等）: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE を利用）。
  - 取得時刻（fetched_at）を UTC ISO8601 で記録し、Look-ahead Bias のトレーサビリティを確保。
  - 型変換ユーティリティ: _to_float, _to_int（安全な変換ロジック、空文字や不正値は None）。

- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - 3層データモデル（Raw / Processed / Feature / Execution）に基づく DDL を提供。
  - テーブル: raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance など多数を定義。
  - 制約・チェック: 型チェック、NOT NULL、CHECK 制約、PRIMARY KEY、FOREIGN KEY を利用してデータ整合性を担保。
  - インデックス: 頻出クエリパターン向けに複数インデックスを作成。
  - init_schema(db_path) によりディレクトリ自動作成と冪等的なテーブル作成を実現。get_connection() で既存 DB に接続。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 日次 ETL エントリポイント run_daily_etl を実装（カレンダー、株価、財務、品質チェックの順で実行）。
  - 差分更新戦略: DB の最終取得日からの差分取得、デフォルトの backfill_days = 3 による後出し修正吸収。
  - カレンダー先読み: デフォルト lookahead_days = 90（日付調整に使用）。
  - ETLResult データクラスを導入し、取得数・保存数・品質問題・エラー等を集約。to_dict によるシリアライズをサポート。
  - 各ステップは独立して例外処理され、1 ステップ失敗でも他ステップを継続（Fail-Fast ではない設計）。
  - run_prices_etl, run_financials_etl, run_calendar_etl などの個別ジョブを提供。
  - 市場日調整ヘルパー _adjust_to_trading_day を提供（market_calendar を参照して非営業日を直近営業日に調整）。

- 監査ログ（audit）モジュール（src/kabusys/data/audit.py）
  - シグナル→発注→約定を UUID 連鎖でトレースする監査スキーマを実装。
  - テーブル: signal_events, order_requests, executions（UTC タイムスタンプを保証）。
  - 冪等性: order_request_id を冪等キーとして設計（重複送信防止）。
  - 状態遷移管理、チェック制約、外部キー（ON DELETE RESTRICT）により監査証跡の保全。
  - init_audit_schema(conn) / init_audit_db(db_path) による初期化を提供。
  - 監査用インデックス群を追加（検索・キュー処理効率化）。

- データ品質チェック（src/kabusys/data/quality.py）
  - QualityIssue データクラスを導入（check_name, table, severity, detail, rows）。
  - 実装済チェック:
    - check_missing_data: raw_prices の OHLC 欠損検出（sample 最大 10 件、重大度 error として報告）。
    - check_spike: 前日比スパイク検出（LAG を用いたウィンドウ関数、デフォルト閾値 50%）。
  - 設計方針として、複数チェック結果を全て収集して呼び出し元に返す（Fail-Fast ではない）。SQL はパラメータバインドを使用。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / 設計上の重要事項
- API 呼び出しはレート制限（120 req/min）を守る設計。429 の場合は Retry-After を優先し、その他は指数バックオフを適用。
- 401 は一度自動リフレッシュを試み、それでも失敗したら例外を返す（無限再帰回避）。
- DuckDB への保存は可能な限り冪等化（ON CONFLICT DO UPDATE）して再実行耐性を持たせている。
- すべての監査・取得時刻は UTC を使って記録（fetched_at, created_at 等）。
- .env パーサは実運用でよくあるフォーマット（export プレフィックス、クォートやエスケープ、インラインコメント）に対応。
- 初期化系関数はディレクトリ自動作成や ":memory:" サポートを持ち、ローカル開発/CI で使いやすい設計。

もし CHANGELOG に追記してほしい点（例: 変更履歴の粒度を増やす、各関数・テーブルごとの導入理由を明記する等）がある場合はお知らせください。