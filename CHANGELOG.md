# Changelog

すべての重要な変更点を日付順で記録します。フォーマットは "Keep a Changelog" に準拠しています。

## [Unreleased]


## [0.1.0] - 2026-03-16
初回公開リリース。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。トップレベルで version を 0.1.0 に設定。
  - 公開サブパッケージ: data, strategy, execution, monitoring（各 __init__ を用意）。

- 環境設定 / config
  - .env ファイルおよび環境変数を読み込む自動ロード機能を実装。
    - ロード優先順位: OS環境変数 > .env.local > .env。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途）。
    - プロジェクトルート検出は __file__ を起点に .git / pyproject.toml を探索するため、CWD に依存しない。
  - .env パーサを実装（コメント、export プレフィックス、クォート／エスケープ対応、インラインコメント処理等）。
  - Settings クラスを提供し、アプリ固有設定をプロパティ経由で取得可能:
    - 必須環境変数チェック: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など。
    - DBパスの既定値（DuckDB: data/kabusys.duckdb、SQLite: data/monitoring.db）と Path 型返却。
    - env 値検証（development / paper_trading / live）およびログレベル検証。
    - ヘルパー: is_live / is_paper / is_dev。

- J-Quants API クライアント（data/jquants_client.py）
  - API クライアントを実装:
    - データ取得: 株価日足 (OHLCV)、財務（四半期 BS/PL）、JPX マーケットカレンダー。
    - レート制御: 固定間隔スロットリングで 120 req/min を順守する RateLimiter を実装。
    - 再試行ロジック: 指数バックオフ（基数 2）で最大 3 回再試行。対象ステータス: 408, 429, 5xx。429 の場合は Retry-After ヘッダを考慮。
    - 401 unauthorized 受信時にはトークン自動リフレッシュを 1 回試みる（無限再帰を防止）。
    - id_token のモジュールレベルキャッシュを提供し、ページネーション間で共有。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - JSON デコード失敗や HTTP エラー時の詳細エラー報告。
  - DuckDB への保存関数を実装（冪等）:
    - save_daily_quotes, save_financial_statements, save_market_calendar：いずれも ON CONFLICT DO UPDATE を使用して重複を排除。
    - fetched_at を UTC ISO 8601 で記録し、Look-ahead Bias のトレーサビリティを確保。
    - 主キー欠損行はスキップし、スキップ数を警告ログに出力。
  - 型変換ユーティリティ: _to_float / _to_int（空値や不正値時は None、"1.0" 形式の取り扱い等を厳密に実装）。

- DuckDB スキーマ管理（data/schema.py）
  - DataPlatform 設計（Raw / Processed / Feature / Execution 層）に基づく豊富な DDL 定義を追加:
    - Raw 層: raw_prices, raw_financials, raw_news, raw_executions
    - Processed 層: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature 層: features, ai_scores
    - Execution 層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - インデックス定義（頻出クエリ向け）を追加。
  - init_schema(db_path) によりディレクトリ自動作成とテーブル／インデックスの冪等作成を実装。
  - get_connection(db_path) を提供（スキーマ初期化を行わない）。

- ETL パイプライン（data/pipeline.py）
  - 日次 ETL のエントリポイント run_daily_etl を実装（市場カレンダー、株価、財務、品質チェックを順次実行）。
  - 差分更新ロジック:
    - 最終取得日を元に自動計算される date_from（デフォルトバックフィル 3 日）で差分取得。
    - 市場カレンダーは先読み（デフォルト 90 日）して営業日調整に利用。
    - 初回ロード時の最古日を定義（2017-01-01）。
  - 個別ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl を提供（それぞれ fetch/save を呼び出す）。
  - ETLResult データクラスを導入し、取得数・保存数・品質問題・エラーを集約して返却。
  - 各ステップは例外を捕捉して継続（1ステップ失敗でも他ステップを続行する設計）。
  - id_token の注入可能性を確保し、テスト容易性を向上。

- 監査ログ（data/audit.py）
  - 戦略 → シグナル → 発注要求 → 約定までトレース可能な監査ログテーブルを定義:
    - signal_events（戦略層シグナルログ）
    - order_requests（冪等キー order_request_id を持つ発注要求ログ）
    - executions（証券会社からの約定ログ）
  - 各テーブルに created_at/updated_at を持たせる設計、UTC タイムゾーン強制設定（SET TimeZone='UTC'）。
  - init_audit_schema(conn) / init_audit_db(db_path) により監査スキーマを冪等に初期化。
  - 外部キー制約、チェック制約、ステータス列、インデックス類を整備。

- データ品質チェック（data/quality.py）
  - QualityIssue データクラスを定義（check_name, table, severity, detail, rows）。
  - チェック実装（DuckDB SQL ベース）:
    - 欠損データ検出 (check_missing_data): raw_prices の OHLC 欄の欠損を検出（volume は許容）。
    - 異常値検出 (check_spike): 前日比スパイク（デフォルト閾値 50%）の検出。LAG ウィンドウ関数を使用。
  - 各チェックは問題のサンプル（最大 10 件）を返し、Fail-Fast とせず全件収集する方針。
  - SQL はパラメータバインド（?）で実行し、インジェクションリスクを低減。

### Notes / その他の設計上のポイント
- 多くの関数が id_token を注入可能に実装されており、テスト用にトークンやモックを差し替え可能。
- DuckDB の接続は ":memory:" を指定してインメモリ DB として利用可能。
- ロギングを各主要処理に追加しており、取得件数、保存件数、スキップ件数、リトライ情報などが出力される。
- API レート制御・リトライ・トークン自動リフレッシュなど、運用を想定した堅牢性を組み込んだ実装。

### Removed
- （該当なし）

### Fixed
- （該当なし）

### Security
- （該当なし）

-----

このリリースは初期実装をまとめたもので、今後のリリースで以下のような項目を順次追加・改善予定です。
- strategy / execution / monitoring 各モジュールの具体的な実装（現状はパッケージプレースホルダ）。
- 追加の品質チェック（重複チェック、日付不整合チェックなどの完成）。
- テストカバレッジと CI ワークフローの整備。
- 実際のブローカー API 統合と発注フロー実装（安全な発注処理、再送制御、部分約定処理等）。