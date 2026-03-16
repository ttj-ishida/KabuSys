# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

最新: [0.1.0] - 2026-03-16

## [Unreleased]
（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-16
初期リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。主な追加内容は以下の通りです。

### 追加 (Added)
- 基本パッケージ
  - パッケージ初期化: kabusys.__init__ に __version__ = "0.1.0" を設定。
  - モジュール公開: data, strategy, execution, monitoring を __all__ に定義。

- 設定管理 (kabusys.config)
  - .env / 環境変数の自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - .env ファイルの堅牢なパーサーを実装（export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いを考慮）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを導入し、J-Quants / kabuステーション / Slack / DB パス / 環境設定（KABUSYS_ENV）/ログレベルを環境変数から取得・検証するプロパティを提供。
  - 必須環境変数未設定時にわかりやすい例外を投げる _require 関数を提供。

- データ取得クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - レート制限 (120 req/min) を守る固定間隔スロットリング RateLimiter を実装。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx 対象）を実装し、429 の場合は Retry-After ヘッダを優先。
  - 401 エラー受信時の自動トークンリフレッシュ（1 回のみ）を実装。get_id_token による ID トークン取得機能あり。
  - ページネーション対応のデータ取得関数を実装:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - データ保存関数（DuckDB 用）を実装し、冪等性を確保（ON CONFLICT DO UPDATE）:
    - save_daily_quotes（raw_prices）
    - save_financial_statements（raw_financials）
    - save_market_calendar（market_calendar）
  - 取得時刻（fetched_at）を UTC ISO8601 形式で記録し、Look-ahead Bias のトレースを可能に。

- スキーマと DB 初期化 (kabusys.data.schema)
  - DuckDB 用の包括的スキーマ定義を実装（Raw / Processed / Feature / Execution 層）。
  - 各種テーブルのDDLを用意（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など）。
  - 性能のためのインデックス定義を追加（銘柄×日付スキャン、ステータス検索などを想定）。
  - init_schema(db_path) でディレクトリ自動作成・テーブル作成を行い、init_schema は冪等（既存テーブルを上書きしない）。
  - get_connection(db_path) で既存 DB への接続を返す。

- ETL パイプライン (kabusys.data.pipeline)
  - 日次 ETL のエントリポイント run_daily_etl を実装。
  - 差分更新ロジックを実装（DB の最終取得日から backfill_days 前から再取得するデフォルト挙動）。
  - 個別ジョブを実装:
    - run_calendar_etl（カレンダーは先読み lookahead_days）
    - run_prices_etl（株価差分）
    - run_financials_etl（財務差分）
  - 各ジョブは独立したエラーハンドリングを行い、1 ステップ失敗でも他ステップを継続。
  - ETL 実行結果を ETLResult データクラスで返却（取得数・保存数・品質問題・エラー一覧等を含む）。
  - カレンダー取得後に target_date を営業日に調整するヘルパーを実装。

- 監査ログ（トレーサビリティ） (kabusys.data.audit)
  - 戦略→シグナル→発注→約定に至るトレーサビリティ用テーブルを実装:
    - signal_events（戦略生成シグナルログ）
    - order_requests（発注要求、order_request_id を冪等キーとして使用）
    - executions（約定ログ、broker_execution_id をユニークキー）
  - すべての TIMESTAMP を UTC で保存する設定を行う（init_audit_schema で SET TimeZone='UTC'）。
  - 監査用インデックス群を追加（処理待ち検索、戦略別検索、broker_order_id 椐付け等）。
  - init_audit_schema / init_audit_db を提供し既存接続への追加や専用 DB 初期化が可能。

- データ品質チェック (kabusys.data.quality)
  - QualityIssue データクラスを定義し、チェック結果を構造化して返却。
  - 主なチェックを実装:
    - check_missing_data: raw_prices の OHLC 欄の欠損検出（必須カラムの欠損は error として報告）。
    - check_spike: 前日比でのスパイク検出（デフォルト閾値 50%）。
    - （重複・日付不整合チェック等の設計に基づく実装方針を反映）。
  - 各チェックはサンプル行（最大 10 件）を返し、Fail-Fast ではなく全件収集方針。

### 変更 (Changed)
- N/A（初期リリースのため該当なし）

### 修正 (Fixed)
- N/A（初期リリースのため該当なし）

### セキュリティ (Security)
- API 認証トークンは環境変数から取得する設計。自動的に .env を上書きしない既定挙動や protected 環境変数保護により誤った上書きを防止。

### 既知の制約・注意点 (Notes)
- J-Quants API のレート制限・リトライは実装済みだが、実運用では追加のバックプレッシャ制御や監視が推奨されます。
- audit テーブルは削除しない前提で設計されており、外部キーは ON DELETE RESTRICT を基本にしています。
- 一部の SQL（特に DuckDB の型/制約）は実環境でのデータ差異により調整が必要になる場合があります。
- テスト用フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動読み込みを無効化できます。
- run_calendar_etl の fetch_market_calendar の引数は内部で holiday_division 等を利用する想定だが、API 側のパラメータ名変更等には注意が必要です。

---

将来的なリリースでは以下を検討しています:
- strategy / execution / monitoring 層の具体的な実装（現在はパッケージ構造のみ）。
- 追加の品質チェック（重複チェック・将来日付検出等）と自動修復オプション。
- 単体テスト・統合テストの追加と CI での DB マイグレーション検証。
- Slack 通知や外部監視の統合（settings に Slack 設定あり）。

(本 CHANGELOG はコードベースから推測して作成しています。実際の変更履歴やリリースノートはプロジェクトの意図に合わせて調整してください。)