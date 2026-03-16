CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従います。  
本リポジトリの初期リリース履歴をコードベースから推測して作成しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

- （現時点では未リリースの変更はありません）

[0.1.0] - 2026-03-16
-------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージメタ情報
    - src/kabusys/__init__.py にてバージョン "0.1.0" を定義、公開モジュールを __all__ で指定。

  - 環境変数 / 設定管理
    - src/kabusys/config.py
      - .env および .env.local をプロジェクトルートから自動読み込み（.git または pyproject.toml を探索してプロジェクトルートを特定）。
      - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途等）。
      - .env の行パーサ実装: export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、行内コメントの扱いを考慮。
      - _load_env_file により OS 環境変数を保護する protected キーセット機能を実装。
      - Settings クラスを提供し、J-Quants / kabu API / Slack / データベースパス 等の設定プロパティを公開。
      - 設定値のバリデーション: KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL（DEBUG/INFO/...）の検証。
      - デフォルト DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"（expanduser 対応）。

  - J-Quants API クライアント
    - src/kabusys/data/jquants_client.py
      - API レート制限（120 req/min）に基づく固定間隔スロットリング実装（内部 RateLimiter）。
      - 冪等性を意識したページネーション取得ロジック。
      - リトライ機構（指数バックオフ、最大 3 回）。HTTP 408/429 と 5xx を自動リトライ。
      - 401 受信時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ共有（ページネーション間でのキャッシュ利用）。
      - get_id_token(): リフレッシュトークンから id_token を取得する POST 処理。
      - データ取得関数: fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar()（pagination 対応）。
      - DuckDB への保存関数: save_daily_quotes(), save_financial_statements(), save_market_calendar()。いずれも ON CONFLICT DO UPDATE により冪等に保存。
      - 取得時刻（fetched_at）を UTC で記録して Look-ahead bias のトレースを容易に。
      - 型変換ヘルパー: _to_float(), _to_int()（不整合値の安全な扱い）。

  - DuckDB スキーマ管理
    - src/kabusys/data/schema.py
      - Raw / Processed / Feature / Execution の四層データモデルに基づく DDL を定義。
      - raw_prices, raw_financials, market_calendar, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など多数のテーブルを定義。
      - 主キー制約、チェック制約、外部キー制約を適用しデータ整合性を強化。
      - 頻出クエリに対するインデックス定義を含む。
      - init_schema(db_path) により DB ファイルの親ディレクトリ自動作成とテーブル初期化を行う（冪等）。
      - get_connection(db_path) で既存 DB に接続可能（スキーマ初期化は行わない）。

  - ETL パイプライン
    - src/kabusys/data/pipeline.py
      - 差分更新（最終取得日を基に未取得分のみ取得）、バックフィル（デフォルト backfill_days=3）およびカレンダー先読み（デフォルト lookahead_days=90）を備えた ETL 実装。
      - ETLResult dataclass を導入し、取得数・保存数・品質問題・エラー一覧を返却。品質問題は詳細を含む形で集約。
      - run_prices_etl(), run_financials_etl(), run_calendar_etl() を提供（個別実行可）。
      - run_daily_etl() によりカレンダー→株価→財務→品質チェックの順で安全に処理。各ステップは独立して例外をキャッチし、他ステップを継続。
      - デフォルトで品質チェックを実行可能（run_quality_checks=True）。

  - 監査ログ（トレーサビリティ）
    - src/kabusys/data/audit.py
      - シグナル→発注要求→約定までの UUID 連鎖によるトレーサビリティ用テーブルを定義: signal_events, order_requests, executions。
      - order_request_id を冪等キーとして扱うことで二重発注の防止をサポート。
      - すべての TIMESTAMP を UTC で保存する方針（init_audit_schema は SET TimeZone='UTC' を実行）。
      - init_audit_schema(conn) および init_audit_db(db_path) を提供（冪等）。

  - データ品質チェック
    - src/kabusys/data/quality.py
      - 欠損データ検出 (open/high/low/close の NULL 検出)
      - 異常値検出（スパイク検出: 前日比の絶対値が閾値を超えた場合、デフォルト閾値 0.5 = 50%）
      - 重複チェック、日付不整合検出のための設計（SQL ベース、パラメータバインド利用）
      - QualityIssue dataclass を導入し、チェック名・対象テーブル・重大度（error/warning）・サンプル行を返却。
      - 各チェックは Fail-Fast ではなく全件収集し、呼び出し元で重大度に応じた判断を可能に。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Deprecated
- 初期リリースのため該当なし。

Security
- 初期リリースのため該当なし（ただし、環境変数の保護やトークン管理、SQL のパラメータバインド等、セキュリティ上の考慮が実装に反映されている）。

Notes / 実装上の重要ポイント
- レート制限は 120 req/min（最小インターバル = 60 / 120 秒）として固定スロットリング方式を採用。
- API リトライは最大 3 回。429 の場合は Retry-After を優先して待機する。
- DuckDB 側の保存は ON CONFLICT DO UPDATE を使用して冪等性を確保。
- ETL は品質チェックでエラーが検出されても（重大度に応じて）処理を継続し、呼び出し元に問題を返す設計。
- 監査ログは削除しない前提でテーブル定義（ON DELETE RESTRICT）や created_at/updated_at の運用を規定。
- .env パーサは export 形式、クォートあり・なし、エスケープ、行内コメントなど多様なフォーマットに対応。

Authors
- コードベースに基づき自動生成した CHANGELOG（実際の作成者はリポジトリのコミット履歴を参照してください）。

上記はコードの内容から推測してまとめた CHANGELOG です。必要であれば項目の追加・修正（細かな仕様値やリリース日など）を行います。