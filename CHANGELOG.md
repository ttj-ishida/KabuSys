# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠しています。  
バージョン番号は Semantic Versioning に従います。

## [Unreleased]

## [0.1.0] - 2026-03-15
初回リリース。日本株自動売買システムの基盤機能を実装しました。

### Added
- パッケージ基盤
  - kabusys パッケージを追加（src/kabusys/__init__.py）。公開 API として data, strategy, execution, monitoring をエクスポート。
  - バージョンを 0.1.0 に設定。

- 設定・環境変数管理
  - 高機能な .env 自動ロード機能を実装（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml から探索して .env/.env.local を自動読み込み（CWD 非依存）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - OS 環境変数を保護（.env.local は既存 OS 変数を上書きしない）。
  - .env パーサは以下に対応：
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント（空白で区切られた # をコメントとして扱う）など。
  - Settings クラスを追加し、環境変数から設定を取得するプロパティを提供（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス、実行環境など）。
    - KABUSYS_ENV の検証（development / paper_trading / live）。
    - LOG_LEVEL の検証（DEBUG, INFO, WARNING, ERROR, CRITICAL）。
    - duckdb/sqlite のデフォルトパスを設定（data/kabusys.duckdb, data/monitoring.db）。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - J-Quants から株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーを取得する fetch_* 関数を実装。
  - 機能:
    - 固定間隔のレートリミット制御（120 req/min）を実装（内部 _RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
    - 401 応答受信時にリフレッシュトークンで自動的に id_token を更新して 1 回だけ再試行。
    - ページネーション対応（pagination_key の追跡・重複検出）。
    - fetched_at を UTC ISO8601 で記録して Look-ahead Bias を防止。
    - JSON デコード失敗時の明瞭なエラー報告。
  - DuckDB への保存用関数を実装（save_daily_quotes / save_financial_statements / save_market_calendar）。
    - INSERT ... ON CONFLICT DO UPDATE により冪等的に保存。
    - PK 欠損行のスキップとログ警告。
    - 値変換ユーティリティ（_to_float, _to_int）を実装し、厳密な変換ルールを適用（不正な小数→ None 等）。

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution の多層データモデルに基づくテーブル定義を追加。
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型チェック・制約（CHECK / PRIMARY KEY / FOREIGN KEY）を付与。
  - 頻出クエリに対するインデックスを定義（例: code×date、status 検索など）。
  - init_schema(db_path) により DB ファイル作成（親ディレクトリ自動作成）および DDL 実行を行う関数を提供。init_schema は冪等。
  - get_connection(db_path) を提供（初期化済み DB への接続取得）。

- 監査ログ（Audit）機能（src/kabusys/data/audit.py）
  - 戦略 → シグナル → 発注要求 → 約定 のトレーサビリティを保証する監査テーブル群を実装。
    - signal_events, order_requests, executions
  - 設計方針に従い、order_request_id を冪等キー、全 TIMESTAMP を UTC で保存する（init_audit_schema は SET TimeZone='UTC' を実行）。
  - 発注種別ごとの制約（limit 注文は limit_price 必須等）、ステータス列、updated_at の運用方針を定義。
  - init_audit_schema(conn) と init_audit_db(db_path) を提供（既存接続に監査テーブルを追加可）。

- モジュール構成
  - data, strategy, execution, monitoring 各パッケージの基本ファイルを追加（空の __init__ を含む）。将来的な拡張用スタブを用意。

### Changed
- なし（初期リリース）。

### Fixed
- なし（初期リリース）。

### Security
- なし（初期リリース）。ただし環境変数読み込みとトークン取り扱いに注意して設計（OS 環境変数の保護等）。

---

注記:
- このリリースは「基盤実装」が中心で、戦略ロジック・実際の発注連携（証券会社 API 呼び出し）は含まれていません。strategy / execution / monitoring パッケージは拡張ポイントとして用意されています。
- DuckDB スキーマは多くの制約・インデックスを設定しているため、将来のマイグレーションでは DDL 互換性に注意してください。