CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
このファイルは日本語で、リポジトリ内の現在のコードベースから推測して作成しています。

Unreleased
----------

- （なし）

0.1.0 - 2026-03-15
-----------------

追加 (Added)
- パッケージ初期リリース "KabuSys" を追加。
  - パッケージメタ情報: src/kabusys/__init__.py にて __version__ = "0.1.0" を定義。
  - モジュール構成: data, strategy, execution, monitoring のパッケージ構成を定義。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは OS 環境変数から設定を読み込む Settings クラスを実装。
  - プロジェクトルートを .git または pyproject.toml から決定する自動検出実装（CWD 非依存）。
  - .env 自動読み込み機構を実装（読み込み優先順位: OS > .env.local > .env）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途）。
  - .env のパースは次の仕様に対応:
    - 空行・コメント行（#）を無視
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - クォートなしの場合はインラインコメントの扱いを柔軟に処理
  - 必須設定を取得する _require() を提供（未設定時に ValueError）。
  - 主要な設定プロパティを実装:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - KABUSYS_ENV（development / paper_trading / live のバリデーション）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のバリデーション）
    - データベースパスのデフォルト: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
    - ヘルパー: is_live / is_paper / is_dev

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API からデータを取得するクライアントを実装:
    - 株価日足（OHLCV）fetch_daily_quotes()
    - 財務データ（四半期 BS/PL）fetch_financial_statements()
    - JPX マーケットカレンダー fetch_market_calendar()
  - 認証トークン取得: get_id_token() を実装（リフレッシュトークン → idToken）。
  - モジュールレベルの ID トークンキャッシュを実装し、ページネーション間で共有。
  - レート制御: 固定間隔スロットリング _RateLimiter（120 req/min、MIN_INTERVAL_SEC 設定）を実装。
  - リトライ戦略:
    - 最大リトライ回数 3 回、指数バックオフを採用（基数: 2.0 秒）。
    - ステータスコード 408/429 および 5xx 系でリトライ。
    - 429 の場合、Retry-After ヘッダを優先して待機。
    - ネットワークエラー（URLError, OSError）に対してもリトライ。
  - 401 Unauthorized を受信した場合、自動でトークンをリフレッシュして 1 回だけリトライ（無限再帰防止）。
  - ページネーションに対応し、pagination_key を用いて全件取得。
  - 取得ログに取得レコード数を出力（logger）。

- DuckDB への永続化ユーティリティ (src/kabusys/data/jquants_client.py)
  - save_daily_quotes(), save_financial_statements(), save_market_calendar() を実装。
  - 保存は冪等（ON CONFLICT DO UPDATE）で重複を排除し上書き。
  - PK 欠損行はスキップし、その件数を警告ログ出力。
  - fetched_at / UTC タイムスタンプを付与し、Look-ahead Bias を防止する設計。

- 型変換ユーティリティ (src/kabusys/data/jquants_client.py)
  - _to_float(), _to_int() を実装:
    - 空値や変換不可は None を返す。
    - _to_int は "1.0" のような小数表現を許容し、ただし小数部が 0 でない場合は None を返す（切り捨て防止）。

- DuckDB スキーマ定義・初期化 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution の 3 層を想定した包括的なスキーマ DDL を実装。
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 多数の CHECK 制約・PRIMARY KEY を付与しデータ整合性を担保。
  - パフォーマンスを考慮したインデックス群を定義（銘柄×日付スキャン、ステータス検索等）。
  - init_schema(db_path) で DB ファイルの親ディレクトリを自動作成し、DDL とインデックスを実行して接続を返す（冪等）。
  - get_connection(db_path) で既存 DB へ接続（初期化は行わない）。

- 監査ログ（Audit / トレーサビリティ） (src/kabusys/data/audit.py)
  - signal_events, order_requests, executions の監査用テーブル群とインデックスを実装。
  - オーダー要求に冪等キー order_request_id を設け、同一キーでの再送を防止する設計。
  - すべての TIMESTAMP を UTC に統一するため、init_audit_schema() 実行時に SET TimeZone='UTC' を実行。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供（既存接続へ追記・専用 DB 初期化）。

- パッケージ空の __init__.py を各サブパッケージに追加（strategy, execution, data, monitoring）。

変更 (Changed)
- （初版のため該当なし）

修正 (Fixed)
- （初版のため該当なし）

削除 (Removed)
- （初版のため該当なし）

非推奨 (Deprecated)
- （初版のため該当なし）

セキュリティ (Security)
- なし（ただし環境変数を必須とする設定や、OS 環境変数を保護する protected 設定など基本的な配慮を実装）。

注意事項 / マイグレーションノート
- .env 自動読み込み
  - 自動読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストでの利用を想定）。
- 必須環境変数
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID が Settings で必須として参照されます。未設定時は ValueError が発生します。
- DuckDB 初期化
  - 初回は data.schema.init_schema(db_path) を使ってスキーマを作成してください。既に作成済みの DB へは get_connection() を使用します。
- 監査ログ
  - 監査テーブルは削除しない想定のため、外部キーは ON DELETE RESTRICT を利用しています。init_audit_schema() を既存の接続に対して実行すると監査用テーブルとインデックスを追加します。
- UTC タイムスタンプ
  - 取得時の fetched_at や監査 TIMESTAMP は UTC で保存する設計になっています。アプリケーション側でも UTC を前提に扱ってください。
- API 利用上の制限
  - J-Quants API 呼び出しは 120 req/min のレート制限を想定しており、クライアント側で待機・リトライ制御を行います。

既知の制約 / TODO（コードから推測）
- strategy, execution, monitoring パッケージは空の __init__ のみであり実装が未着手（今後追加予定）。
- DuckDB の永続層と監査層の連携ロジック（アプリケーションレベルでのイベント登録や order_request_id の生成・扱い）はアプリ側実装が必要。
- J-Quants の API スキーマ変更や追加のエンドポイントは現状サポート外。

ライセンスや貢献ガイド等のメタ情報はコードベースからは推測できないため本CHANGELOGには含めていません。必要であれば追加情報をください。