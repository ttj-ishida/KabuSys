# Changelog

すべての重要な変更をここに記録します。本ファイルは Keep a Changelog の形式に準拠します。

現在のバージョンの命名規則: MAJOR.MINOR.PATCH  
リリース日は年月日 (YYYY-MM-DD) で記載します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-15

初回リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。以下は主な追加点と設計上の重要事項です。

### 追加 (Added)
- パッケージ化
  - パッケージルートにバージョン情報を実装: kabusys.__version__ = "0.1.0"
  - 主要サブパッケージを公開: data, strategy, execution, monitoring

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイル及び OS 環境変数を透過的に読み込む自動ロード機構を実装
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - パッケージ内からプロジェクトルートを .git または pyproject.toml を基準に探索するため、CWD に依存せず動作
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
  - .env パーサーの実装
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュによるエスケープ、行末コメントの取り扱い等に対応
    - 無効行（空行やコメント）をスキップ
  - 環境設定ラッパークラス Settings を提供
    - J-Quants / kabuステーション / Slack / DB パス 等のプロパティを定義
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の検証ロジック
    - パス系値（duckdb/sqlite）は Path に変換し展開

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API 呼び出し共通処理を実装
    - レート制限 (120 req/min) を固定間隔スロットリングで強制する RateLimiter を実装
    - リトライ戦略: 指数バックオフ、最大 3 回、対象ステータス 408/429/5xx、429 は Retry-After 優先
    - 401 Unauthorized に対しては自動でトークンをリフレッシュして 1 回だけリトライ
    - ページネーション対応（pagination_key）
    - JSON デコードエラーやネットワークエラーのハンドリング
    - モジュールレベルで ID トークンをキャッシュし、ページネーション間で共有
  - 認証: get_id_token(refresh_token=None) を実装（refresh_token は settings から取得可能）
  - データ取得関数を提供
    - fetch_daily_quotes(code/date_from/date_to) — 日足（OHLCV）
    - fetch_financial_statements(code/date_from/date_to) — 財務（四半期 BS/PL）
    - fetch_market_calendar(holiday_division) — JPX マーケットカレンダー
    - 取得時にログ出力（取得件数）
    - Look-ahead バイアス対策のため取得時刻 (fetched_at) を UTC で記録することを設計方針として明記
  - DuckDB への保存関数を提供（冪等）
    - save_daily_quotes(conn, records) — raw_prices へ INSERT ... ON CONFLICT DO UPDATE
    - save_financial_statements(conn, records) — raw_financials へ冪等保存
    - save_market_calendar(conn, records) — market_calendar へ冪等保存（HolidayDivision を取引日/半日/SQ 判定）
    - PK 欠損行はスキップしてログに警告出力
  - データ型変換ユーティリティ
    - _to_float: 空値や変換失敗時に None を返す
    - _to_int: "1.0" のような float 文字列は float 経由で変換し、小数部が非ゼロの場合は None を返す（意図しない切り捨て防止）

- DuckDB スキーマ定義・初期化 (src/kabusys/data/schema.py)
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）+ Execution レイヤのテーブル DDL を定義
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 監査（audit）用のテーブル作成を意識した外部キー順序でのテーブル作成
  - 頻出クエリ向けに複数のインデックスを定義（銘柄×日付、ステータス検索等）
  - init_schema(db_path) により DB ファイル（または ":memory:"）を初期化して接続を返す（親ディレクトリ自動作成）
  - get_connection(db_path) により既存 DB へ接続（初期化は行わない）

- 監査ログ（トレーサビリティ）モジュール (src/kabusys/data/audit.py)
  - シグナル〜発注〜約定の監査テーブルを定義
    - signal_events: 戦略が生成したシグナル（棄却やエラーも含む）
    - order_requests: 発注要求（order_request_id を冪等キーとして採用、各種チェック制約あり）
    - executions: 証券会社から返される約定ログ（broker_execution_id をユニークな冪等キーとして扱う）
  - すべての TIMESTAMP は UTC で保存（init_audit_schema は SET TimeZone='UTC' を実行）
  - ON DELETE RESTRICT を基本とし、監査ログは削除しない方針
  - インデックスを作成し、検索性とコールバック紐付け（broker_order_id）に配慮
  - init_audit_schema(conn) で既存接続に監査テーブルを追記、init_audit_db(db_path) による専用 DB 初期化を提供

### 変更 (Changed)
- 初期リリースのため変更履歴はありません（将来のリリースで記載）。

### 修正 (Fixed)
- 初期リリースのため修正履歴はありません。

### 注意事項 / 設計メモ
- J-Quants API のレート制限を厳守するため内部で固定間隔のスロットリングを行います。大量取得や並列化する場合はこの設計を考慮してください。
- get_id_token はリフレッシュトークン必須（settings.jquants_refresh_token を使用）。テスト等で自動ロードを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のスキーマは多くの制約（CHECK / FOREIGN KEY / PRIMARY KEY）を含みます。既存スキーマへの差分適用は慎重に行ってください。
- 監査テーブルは削除を想定していない設計です。履歴保持を前提とした運用を想定しています。

以上。今後のリリースでは具体的なバグ修正、機能追加（戦略ロジック、実行エンジン、モニタリング、Slack 通知等）をこの CHANGELOG に記載します。