# Changelog

すべての重要な変更をここに記録します。本ドキュメントは Keep a Changelog のガイドラインに従って作成されています。  
フォーマット: https://keepachangelog.com/ (日本語)

## [Unreleased]
今後のリリース向けの保留中変更はここに記載します。

---

## [0.1.0] - 2026-03-16

初回公開リリース。日本株自動売買システムの基盤機能を実装しています。主に設定管理、外部データ取得・保存周り（J-Quants API + DuckDB）、監査ログスキーマ、データ品質チェックに関する機能を含みます。

### Added
- パッケージ基礎
  - パッケージ名: kabusys、パッケージバージョンを `__version__ = "0.1.0"` に設定。
  - パッケージ公開対象として data, strategy, execution, monitoring を __all__ で公開。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機能を実装（優先順位: OS 環境変数 > .env.local > .env）。
  - .env 解析機能: コメント行、export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの取り扱いに対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
  - 必須変数取得のヘルパー _require() を提供（未設定時は ValueError）。
  - 各種設定プロパティを実装:
    - J-Quants 用: jquants_refresh_token
    - kabuAPI 用: kabu_api_password, kabu_api_base_url
    - Slack 用: slack_bot_token, slack_channel_id
    - DB パス: duckdb_path, sqlite_path（既定値付き）
    - システム設定: env（development/paper_trading/live の検証）、log_level の検証、is_live / is_paper / is_dev ヘルパー

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API ベースの HTTP リクエストユーティリティを実装。
  - レート制御: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter を追加。
  - 再試行/バックオフロジック:
    - 最大リトライ回数 3 回、指数バックオフ（base=2.0 秒）。
    - 対象ステータス: 408, 429, および 5xx。
    - 429 の場合は Retry-After ヘッダを優先。
  - トークン管理:
    - get_id_token() によるリフレッシュトークン→IDトークン取得（POST）。
    - モジュールレベルで ID トークンをキャッシュし、401 受信時に自動リフレッシュして 1 回リトライ。
    - get_id_token 呼び出し時の無限再帰防止フラグ。
  - ページネーション対応のデータ取得関数:
    - fetch_daily_quotes (OHLCV、ページネーション対応)
    - fetch_financial_statements (四半期 BS/PL、ページネーション対応)
    - fetch_market_calendar (JPX マーケットカレンダー)
  - 取得設計:
    - fetched_at を UTC タイムスタンプで記録し、Look-ahead bias を防止する設計思想を反映。
    - JSON デコード失敗時や HTTP エラー時の明確なログ/例外化。

- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - 3 層（Raw / Processed / Feature）+ Execution 層を想定したスキーマ定義を追加。
  - Raw テーブル: raw_prices, raw_financials, raw_news, raw_executions
  - Processed テーブル: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - Feature テーブル: features, ai_scores
  - Execution テーブル: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 多数の制約（PRIMARY KEY、CHECK、FOREIGN KEY）および頻出クエリ用インデックスを定義。
  - init_schema(db_path) による初期化関数を提供（ディレクトリ自動作成、冪等実行）。
  - get_connection(db_path) による既存 DB 接続の取得を提供（初期化は行わない旨を明記）。

- DuckDB への保存ユーティリティ (src/kabusys/data/jquants_client.py)
  - fetch の結果を DuckDB に保存する冪等な save_ 関数を実装:
    - save_daily_quotes: raw_prices に ON CONFLICT DO UPDATE で保存
    - save_financial_statements: raw_financials に ON CONFLICT DO UPDATE で保存
    - save_market_calendar: market_calendar に ON CONFLICT DO UPDATE で保存
  - PK 欠損行のスキップ、スキップ数のログ出力、fetched_at の一貫した UTC 記録。

- 監査ログ（Audit）スキーマ (src/kabusys/data/audit.py)
  - シグナル → 発注要求 → 約定 までの追跡を目的とした監査テーブルを追加:
    - signal_events（シグナル生成ログ）
    - order_requests（発注要求、order_request_id を冪等キーとして採用）
    - executions（証券会社からの約定ログ）
  - 状態遷移／ステータス列、制約、インデックスを定義。
  - init_audit_schema(conn) により既存 DuckDB 接続へ監査テーブルを追加（UTC タイムゾーン強制）。
  - init_audit_db(db_path) で監査専用 DB を初期化して接続を返す機能を提供。

- データ品質チェックモジュール (src/kabusys/data/quality.py)
  - QualityIssue データクラスを定義してチェック結果を構造化。
  - チェック実装:
    - check_missing_data: raw_prices の OHLC 欠損検出（必須カラム: open/high/low/close）
    - check_spike: 前日比スパイク検出（デフォルト閾値 50%）
    - check_duplicates: raw_prices の主キー重複検出
    - check_date_consistency: 将来日付チェックおよび market_calendar との非営業日整合性チェック
  - run_all_checks: 上記チェックをまとめて実行し、すべての QualityIssue を返す。
  - 各チェックはサンプル行（最大 10 件）を返し、Fail-Fast ではなく全件収集する設計。

- その他
  - 空のパッケージ初期化ファイル: execution/__init__.py, strategy/__init__.py, data/__init__.py, monitoring/__init__.py（将来の拡張を想定）。

### Changed
- 初版リリースのため該当なし。

### Fixed
- 初版リリースのため該当なし。

### Security
- HTTP リクエストでタイムアウトを設定（30 秒）。
- .env の自動読み込み時に OS 環境変数を保護する設計（protected set）を採用。

### Notes / Design Decisions
- J-Quants API のレート制限（120 req/min）を厳守するため固定間隔スロットリングを採用。簡易な設計だがレート超過防止には有効。
- id_token はモジュールレベルでキャッシュしページネーション間で共有することで余分なトークン取得を抑制する。
- DuckDB DDL は冪等（CREATE TABLE IF NOT EXISTS、INDEX の IF NOT EXISTS）とし、初回以外の再実行を安全化。
- 監査ログは削除しない前提（FK は ON DELETE RESTRICT）で設計し、トレーサビリティを重視。
- すべての TIMESTAMP は UTC で扱う（監査スキーマの初期化時に SET TimeZone='UTC' を実行）。

---

今後のリリースでは、戦略実装、発注実行ロジック（kabuステーション連携）、Slack 通知、モニタリング機能、テストカバレッジと CI/CD の追加を予定しています。必要であればこの CHANGELOG を英語版に翻訳したり、リリースノートを項目ごとに細分化したりできます。