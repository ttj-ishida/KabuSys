CHANGELOG
=========

すべての変更は「Keep a Changelog」の形式に従って記載しています。
セマンティックバージョニングを使用しています。

[Unreleased]
-------------

（現在未リリースの変更はありません）

[0.1.0] - 2026-03-16
-------------------

Added
- 初回リリース。KabuSys 日本株自動売買システムのコアモジュールを追加。
  - パッケージ初期化:
    - パッケージバージョンを `__version__ = "0.1.0"` として定義。
    - パッケージの公開モジュールを `__all__ = ["data", "strategy", "execution", "monitoring"]` に設定。
  - 設定（config）:
    - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
      - プロジェクトルートを .git または pyproject.toml を基準に探索して .env / .env.local を読み込む。
      - 環境変数による自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
      - `.env.local` は `.env` を上書きする挙動（OS 環境変数は保護）。
    - .env のパース処理を強化（コメント、export プレフィックス、シングル/ダブルクォート内エスケープ対応）。
    - Settings クラスを提供し、アプリケーションで必要な設定プロパティを集中管理。
      - J-Quants / kabuステーション / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル等。
      - 必須変数未設定時は ValueError を送出する `_require()` を用意。
  - データ取得（data/jquants_client.py）:
    - J-Quants API クライアントを実装。
      - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する fetch_* 関数群。
      - ページネーション対応（pagination_key を利用してページ繰り）。
      - モジュールレベルで ID トークンのキャッシュを保持し、ページネーション間で共有。
      - レート制限（120 req/min）を固定間隔スロットリングで厳守する RateLimiter を実装。
      - 再試行（リトライ）ロジックを実装：指数バックオフ、最大 3 回、HTTP 408/429/5xx を対象。
      - 401 受信時はリフレッシュトークンから id_token を再取得して1回リトライ（無限再帰防止のため allow_refresh 制御）。
      - JSON デコードエラー時の明確な例外化。
    - DuckDB への冪等な保存関数 save_* を提供（ON CONFLICT DO UPDATE を利用）。
      - save_daily_quotes / save_financial_statements / save_market_calendar を実装。
      - PK 欠損レコードをスキップしログ出力。
      - 保存時に fetched_at を UTC ISO 8601 形式で付与。
    - 入出力データの型変換ユーティリティ `_to_float`, `_to_int` を実装（型安全な取り扱い）。
  - DuckDB スキーマ（data/schema.py）:
    - DataPlatform の3層構造（Raw / Processed / Feature）と Execution 層のテーブル定義を追加。
      - Raw: raw_prices, raw_financials, raw_news, raw_executions
      - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - Feature: features, ai_scores
      - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 運用上有用なインデックスを作成（銘柄×日付スキャン、ステータス検索等）。
    - init_schema(db_path) による初期化関数を提供（親ディレクトリ自動作成、:memory:対応、冪等）。
    - 既存 DB へ接続する get_connection を提供（初期化は行わない旨を明記）。
  - ETL パイプライン（data/pipeline.py）:
    - 日次 ETL のエントリ run_daily_etl を実装し、処理フローを統合。
      - 処理順: 市場カレンダー取得（先読み）→ 株価差分取得（バックフィル）→ 財務差分取得 → 品質チェック（任意）
      - 差分更新ロジック（DB の最終取得日を基に自動算出）とデフォルトバックフィル日数（3日）に対応。
      - 市場カレンダーは先読み（デフォルト 90 日）することで営業日調整に使用。
      - 各ステップは独立して例外処理され、1ステップ失敗でも他ステップは継続（エラーは ETLResult に蓄積）。
    - ETLResult データクラスを導入（取得件数、保存件数、品質問題、エラー一覧、ユーティリティメソッド含む）。
    - 日付の営業日調整ヘルパー（_adjust_to_trading_day）を実装。
    - 差分判定用の get_last_* ヘルパーを提供（raw_prices/raw_financials/market_calendar）。
  - 監査ログ（data/audit.py）:
    - シグナルから約定に至る監査用テーブル定義を追加（signal_events, order_requests, executions）。
    - 監査テーブル初期化関数 init_audit_schema / init_audit_db を提供。
    - 監査用インデックスを整備（処理待ちキュー検索、broker_id 紐付け等）。
    - すべての TIMESTAMP を UTC で保存する方針を採用（init で SET TimeZone='UTC' を実行）。
    - 冪等キー（order_request_id, broker_execution_id 等）や状態遷移モデルを設計文書として注記。
  - 品質チェック（data/quality.py）:
    - データ品質チェック機能を実装。
      - 欠損データ検出（raw_prices の OHLC 欠損） → QualityIssue（severity="error"）を返却。
      - スパイク検出（前日比の変動が閾値を超える）を実装（デフォルト閾値 50%）。
      - 重複チェック、日付不整合チェック等を想定した設計（SQL ベースで効率化）。
    - QualityIssue データクラスを定義し、チェック名・テーブル・重大度・サンプル行等を返す形式に統一。
  - パッケージ構成:
    - data パッケージ内に jquants_client, schema, pipeline, audit, quality を実装。
    - strategy / execution / monitoring のパッケージプレースホルダを追加（将来拡張のための初期構成）。

Changed
- （初回リリースにつき該当なし）

Fixed
- （初回リリースにつき該当なし。ただし多くの部分で堅牢性を考慮した実装（リトライ、レート制御、入力パース、型変換、冪等性）が施されています）.

Security
- 機密情報（トークン等）は Settings を通して環境変数で管理することを想定。.env の自動読み込みはテスト等のために無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Notes / Migration
- 初回セットアップ:
  - DuckDB スキーマを初期化するには data.schema.init_schema(db_path) を呼び出してください。
  - 監査ログを別 DB に分ける場合は data.audit.init_audit_db() を使用、既存接続に追加する場合は init_audit_schema(conn) を使用してください。
- 必須環境変数（例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - DB パスは `DUCKDB_PATH` / `SQLITE_PATH`（デフォルトは data/ 以下）。
- J-Quants API の利用:
  - レート制限・リトライ・トークンリフレッシュはライブラリ側で管理しますが、API 利用量には注意してください。
- 品質チェック:
  - ETL 実行後に品質チェックを行い、重大な品質問題（severity="error"）は ETLResult.has_quality_errors で検出できます。呼び出し側で取り扱いを行ってください。

Acknowledgments
- このリリースはコアデータ基盤（ETL・スキーマ・監査・品質）を中心に実装しており、今後 strategy / execution / monitoring 層の機能追加を予定しています。