CHANGELOG
=========
All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and uses Semantic Versioning.

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-15
--------------------

Added
- パッケージ初回リリース。
- 基本パッケージ構成を追加:
  - kabusys (トップパッケージ)
  - サブパッケージ: data, strategy, execution, monitoring（strategy/execution/monitoring は初期プレースホルダ）。
- バージョン情報:
  - パッケージバージョンを 0.1.0 に設定。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード:
    - プロジェクトルートを .git または pyproject.toml で検出して .env/.env.local を自動読み込み。
    - 読み込み順序: OS環境変数 > .env.local (上書き) > .env（未設定キーのみ設定）。
    - 自動ロードを無効化するために環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサ:
    - 空行・コメント行・`export KEY=val` 形式に対応。
    - クォート（シングル/ダブル）内のバックスラッシュエスケープに対応。
    - クォートなしの場合、`#` の扱いはインラインコメントの検出ルールを実装。
  - 必須設定の取得を行う _require 関数を提供（設定未存在時は ValueError を送出）。
  - Settings で各種設定プロパティを提供:
    - J-Quants: JQUANTS_REFRESH_TOKEN（必須）
    - Kabu Station: KABU_API_PASSWORD（必須）、KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - Slack: SLACK_BOT_TOKEN（必須）、SLACK_CHANNEL_ID（必須）
    - データベース既定パス: DUCKDB_PATH（data/kabusys.duckdb）, SQLITE_PATH（data/monitoring.db）
    - 実行環境: KABUSYS_ENV（development / paper_trading / live の検証）と LOG_LEVEL（DEBUG/INFO/... の検証）
    - ヘルパー: is_live / is_paper / is_dev

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 呼び出しユーティリティを追加:
    - ベース URL: https://api.jquants.com/v1
    - レート制限: 120 req/min を固定間隔スロットリングで制御（_RateLimiter）。
    - リトライポリシー: 最大 3 回、指数バックオフ（ベース 2 秒）、リトライ対象ステータス 408/429/5xx。
    - 429 の場合は Retry-After ヘッダを優先して待機。
    - 401 エラー発生時は ID トークンを自動リフレッシュして 1 回のみ再試行（無限再帰回避）。
    - ページネーション対応。ページネーションキーの重複チェックでループを終了。
    - モジュールレベルの ID トークンキャッシュを導入（ページネーション間でトークン共有）。
  - 提供するデータ取得関数:
    - fetch_daily_quotes: 日足（OHLCV）取得（code, date_from, date_to に対応）
    - fetch_financial_statements: 四半期財務（BS/PL）取得
    - fetch_market_calendar: JPX マーケットカレンダー取得（祝日・半日・SQ）
    - 取得関数は取得日時（fetched_at）を UTC で把握できるよう設計方針を明記。
  - 認証:
    - get_id_token(refresh_token=None) を提供（POST /token/auth_refresh を呼び出し idToken を返す）。
    - refresh_token は settings.jquants_refresh_token を用いる（未設定時は ValueError）。

  - 型変換ユーティリティ:
    - _to_float: None / 空文字列 / 変換失敗時に None を返す。
    - _to_int: "1.0" のような float 文字列は float 経由で変換するが、小数部が 0 でない場合は None を返す（意図しない切り捨て防止）。

- DuckDB スキーマ定義と初期化 (kabusys.data.schema)
  - 3 層データレイヤー（Raw / Processed / Feature）に加え Execution 層の DDL を定義。
  - Raw Layer テーブル: raw_prices, raw_financials, raw_news, raw_executions
  - Processed Layer テーブル: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - Feature Layer テーブル: features, ai_scores
  - Execution Layer テーブル: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型制約、CHECK 条項、PRIMARY KEY、外部キー（必要箇所）を付与。
  - パフォーマンス用インデックスを複数定義（例: idx_prices_daily_code_date, idx_signal_queue_status, idx_orders_status など）。
  - init_schema(db_path) を実装:
    - 指定したパスの親ディレクトリを自動作成（:memory: を除く）。
    - 全 DDL とインデックスを実行して冪等的にテーブルを作成し DuckDB 接続を返す。
  - get_connection(db_path) を提供（既存 DB への接続を返す。初回は init_schema を推奨）。

- 監査ログ / トレーサビリティ (kabusys.data.audit)
  - 戦略→シグナル→発注→約定のトレーサビリティを提供する監査テーブルを追加。
  - トレーサビリティ設計に基づく DDL:
    - signal_events: 戦略が生成したシグナルと最終判定（リジェクト理由等）を記録
    - order_requests: 発注要求（order_request_id を冪等キーとして採用）、limit/stop のチェック制約を実装
    - executions: 証券会社の約定情報（broker_execution_id をユニーク冪等キーとして保持）
  - インデックス: 日付・銘柄検索、戦略別検索、status によるキュー検索、broker_order_id による紐付け等を最適化するインデックス群を追加。
  - init_audit_schema(conn) と init_audit_db(db_path) を提供:
    - すべての TIMESTAMP を UTC で保存するために接続で SET TimeZone='UTC' を実行。
    - 既存接続へ監査用テーブルを冪等的に追加できる。

- データ保存ユーティリティ
  - save_daily_quotes(conn, records): raw_prices への冪等的保存（ON CONFLICT DO UPDATE）を実装。
  - save_financial_statements(conn, records): raw_financials への冪等的保存を実装。
  - save_market_calendar(conn, records): market_calendar への冪等的保存を実装。
  - 保存処理は PK 欠損行をスキップし、その件数をログ警告する挙動を実装。
  - 保存時に fetched_at を UTC ISO 形式で記録（Z 表記）。

Changed
- 初版の設計原則をコメント/ドキュメントに明記（レート制限順守、リトライ、冪等性、トレーサビリティ等）。

Fixed
- なし（初版）

Security
- 認証トークンに関する挙動を明確化:
  - id_token はキャッシュされ、必要に応じて自動リフレッシュされる（401→1回のみ）。
  - .env ファイル読み込み時に OS 環境変数を保護（protected set）し、意図しない上書きを防止。

Notes
- 実装はユーティリティ中心の初期基盤であり、strategy / execution / monitoring の具体的ロジックは今後実装予定。
- DuckDB スキーマは冪等に作成されるため、既存 DB に対して繰り返し初期化を呼んでも安全。
- J-Quants 客のネットワーク/HTTP エラー処理・リトライは汎用的な設計を採用しているが、本番運用ではさらに監視・メトリクス収集を検討してください。