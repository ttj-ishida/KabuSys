# CHANGELOG

このファイルは Keep a Changelog の形式に準拠しています。  
安定化・互換性ポリシーはセマンティックバージョニング (SemVer) に従います。

全般的な注意:
- 日時は UTC を前提に保存する設計になっています（特に監査ログ / fetched_at）。
- DuckDB をデータストアとして使用。スキーマは冪等に作成され、既存データを壊さないよう設計されています。

## [Unreleased]
（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-15
初回リリース

### 追加 (Added)
- パッケージの基本構成
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境設定・読み込み (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を自動読み込みする機能を実装。
  - プロジェクトルート検出: __file__ を基点に .git または pyproject.toml を探索してルートを特定。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサ: コメント、export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメント処理等に対応。
  - 環境設定ラッパー Settings を提供。主要プロパティ:
    - jquants_refresh_token (必須)
    - kabu_api_password (必須)
    - kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
    - slack_bot_token, slack_channel_id (必須)
    - duckdb_path (デフォルト: data/kabusys.duckdb)
    - sqlite_path (デフォルト: data/monitoring.db)
    - KABUSYS_ENV 検証（development / paper_trading / live）
    - LOG_LEVEL 検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev ヘルパー

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API ベース実装: ID トークン取得、日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得関数を実装。
  - レート制限: 固定間隔スロットリングで 120 req/min を保証する RateLimiter を実装。
  - リトライロジック: 指数バックオフ、最大 3 回リトライ（対象: 408/429/5xx、およびネットワークエラー）。
  - 401 ハンドリング: 401 受信時に自動でトークンをリフレッシュして 1 回再試行（無限再帰防止）。
  - ページネーション対応: pagination_key を用いた全ページ取得。
  - id_token キャッシュ: モジュールレベルでキャッシュしてページ間で共有可能。
  - fetched_at: データ取得時刻を UTC ISO8601 で付与して Look-ahead Bias を防止。
  - 取得結果保存用関数（DuckDB へ保存）:
    - save_daily_quotes: raw_prices テーブルへ挿入（ON CONFLICT DO UPDATE により冪等性を確保）
    - save_financial_statements: raw_financials テーブルへ挿入（冪等）
    - save_market_calendar: market_calendar テーブルへ挿入（HolidayDivision を is_trading_day / is_half_day / is_sq_day に変換）
  - 型変換ユーティリティ: _to_float / _to_int（安全な変換ロジック、空値や不正値を None に変換）

- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - 3 層（Raw / Processed / Feature） + Execution 層のテーブル DDL を定義。
  - Raw 層（raw_prices, raw_financials, raw_news, raw_executions）
  - Processed 層（prices_daily, market_calendar, fundamentals, news_articles, news_symbols）
  - Feature 層（features, ai_scores）
  - Execution 層（signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）
  - 頻出クエリ用インデックス定義を含む（銘柄×日付のスキャンやステータス検索等を想定）。
  - init_schema(db_path) により DB ファイルの親ディレクトリを自動作成し、テーブルとインデックスを冪等で作成。
  - get_connection(db_path) で既存 DB への接続を返す（スキーマ初期化は行わない）。

- 監査ログ（トレーサビリティ） (src/kabusys/data/audit.py)
  - シグナルから約定に至るトレーサビリティ用テーブルを定義。
  - トレーサビリティ階層と設計方針を実装（order_request_id を冪等キー、削除不可、UTC タイムスタンプ等）。
  - DDL:
    - signal_events: 戦略が生成したシグナル全履歴（棄却やエラー含む）
    - order_requests: 発注要求（order_request_id が冪等キー、各種整合性チェック）
    - executions: 証券会社からの約定ログ（broker_execution_id をユニークキー）
  - インデックス: 迅速な検索・JOIN を行うための複数のインデックスを作成。
  - API:
    - init_audit_schema(conn): 既存の接続に監査用テーブルを追加（UTC タイムゾーンを設定）
    - init_audit_db(db_path): 監査専用 DB の初期化および接続返却

- モジュール構造
  - src/kabusys/__init__.py: __version__ を定義し、主要サブモジュール（data, strategy, execution, monitoring）を __all__ に登録。
  - 空のパッケージプレースホルダ: src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/data/__init__.py, src/kabusys/monitoring/__init__.py を配置（将来的な拡張を想定）。

### 変更 (Changed)
- 初回リリースにつき該当なし

### 修正 (Fixed)
- 初回リリースにつき該当なし

### 削除 (Removed)
- 初回リリースにつき該当なし

### セキュリティ (Security)
- 初回リリースにつき該当なし

---

参考: 初期リリースにおける利用上の注意点
- 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を設定してください。
- DuckDB 初期化時にデータディレクトリが自動作成されます（デフォルト: data/kabusys.duckdb）。
- J-Quants API のレート制限と再試行ポリシーを組み込んでいますが、長時間の大量取得時は追加の制御（並列化制限など）をご検討ください。

（必要なら今後のリリースノートに移行・既知の問題・マイグレーション手順などを追加します。）