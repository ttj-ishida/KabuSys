# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このファイルはパッケージのソースコードから推測して作成した初回リリースの変更履歴です。

全体のバージョンはパッケージ定義 (src/kabusys/__init__.py) に基づく 0.1.0 です。

[0.1.0] - 2026-03-16
-------------------

Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys
  - エクスポート: data, strategy, execution, monitoring

- 環境変数・設定管理モジュールを追加 (src/kabusys/config.py)
  - .env ファイルおよび OS 環境変数から設定を読み込む自動ロード機能を実装
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - プロジェクトルートの判定は .git または pyproject.toml に基づき行うため、CWD に依存しない
  - .env パーサ: export 形式、引用符でのエスケープ、インラインコメント判定などを考慮した安全なパーサを実装
  - Settings クラスを提供（プロパティで各種必須・任意設定を取得）
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として検証
    - データベースパスの既定値: DUCKDB_PATH=data/kabusys.duckdb、SQLITE_PATH=data/monitoring.db
    - 環境種別 KABUSYS_ENV の検証（development / paper_trading / live）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）

- J-Quants API クライアントを追加 (src/kabusys/data/jquants_client.py)
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得機能
  - レート制限制御 (_RateLimiter): 120 req/min（固定間隔スロットリング）
  - リトライ戦略: 指数バックオフ、最大 3 回、対象ステータス 408/429/5xx、429 の場合は Retry-After を尊重
  - 401 発生時はリフレッシュトークンから id_token を自動取得して 1 回リトライ（無限再帰を防止）
  - ページネーション対応（pagination_key を用いたループ取得）とモジュールレベルの id_token キャッシュ
  - DuckDB への保存関数（save_*）は冪等化（ON CONFLICT DO UPDATE）され、fetched_at を UTC で記録
  - 型変換ユーティリティ (_to_float, _to_int) を実装（不正値は None）

- DuckDB スキーマ定義・初期化モジュールを追加 (src/kabusys/data/schema.py)
  - 3 層データモデルを実装（Raw / Processed / Feature / Execution）
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブル定義
  - prices_daily, market_calendar, fundamentals, features, ai_scores 等の Processed/Feature テーブル定義
  - signals, signal_queue, orders, trades, positions, portfolio_performance などの Execution 層テーブル定義
  - パフォーマンスを考慮したインデックス定義
  - init_schema(db_path) によりディレクトリ自動作成を行い、DDL とインデックスを冪等に実行して接続を返す
  - get_connection(db_path) で既存 DB へ接続（スキーマ初期化は行わない）

- ETL パイプラインを追加 (src/kabusys/data/pipeline.py)
  - 日次 ETL のエントリ run_daily_etl を提供（市場カレンダー → 株価 → 財務 → 品質チェックの順）
  - 差分更新ロジック:
    - DB の最終取得日を参照し、未取得分のみを取得
    - backfill_days（デフォルト 3 日）により最終取得日の数日前から再取得して API 後出し修正を吸収
    - 市場カレンダーは lookahead_days（デフォルト 90 日）先まで先読み
  - 各 ETL ステップは独立して例外をハンドリング。1 ステップ失敗でも他は継続し、エラー概要を ETLResult に集約
  - ETLResult データクラス: 取得件数・保存件数・品質問題・エラー一覧・ヘルパーメソッドを提供
  - ETL 内で jquants_client の fetch_* / save_* を利用して冪等に保存

- 監査ログ（トレーサビリティ）モジュールを追加 (src/kabusys/data/audit.py)
  - Signal → OrderRequest → Execution の UUID 連鎖でフローをトレースする監査テーブル群を定義
  - signal_events, order_requests, executions の DDL を実装
  - order_requests に冪等キー（order_request_id）を採用し、各種チェック制約（limit/stop の価格制約等）を定義
  - init_audit_schema(conn) / init_audit_db(db_path) により監査用スキーマを冪等に初期化
  - すべての TIMESTAMP を UTC で保存するため init_audit_schema は SET TimeZone='UTC' を実行
  - インデックスを整備（status 検索や broker_order_id による紐付け等）

- データ品質チェックモジュールを追加 (src/kabusys/data/quality.py)
  - チェック項目:
    - 欠損データ検出（raw_prices の OHLC 欠損） → QualityIssue(severity="error")
    - スパイク検出（前日比変動率の絶対値 > threshold）。デフォルト閾値は 0.5（50%）
    - 重複、日付不整合（将来日付や営業日外）などを想定（実装は SQL ベースで効率的に実行）
  - QualityIssue データクラス（check_name, table, severity, detail, rows）を提供
  - 各チェックはサンプル行（最大 10 件）と問題件数を返す設計（Fail-Fast ではなく全件収集）

- パッケージ内ユーティリティと初期ファイルを追加
  - src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/data/__init__.py を空のパッケージとして作成（今後の拡張場所）

Notes / Usage
- 初期化例
  - DB スキーマの初期化:
    - from kabusys.data.schema import init_schema
    - conn = init_schema(settings.duckdb_path)
  - 監査スキーマの追加:
    - from kabusys.data.audit import init_audit_schema
    - init_audit_schema(conn)
  - 日次 ETL 実行:
    - from kabusys.data.pipeline import run_daily_etl
    - result = run_daily_etl(conn)
- 必須環境変数
  - JQUANTS_REFRESH_TOKEN（J-Quants）、KABU_API_PASSWORD（kabu API）、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID
  - Settings のプロパティ参照時に未設定だと ValueError が発生するため、運用前に .env を準備すること
- 自動 .env ロード
  - プロジェクトルートが特定できない場合、自動ロードはスキップされる（テストなどで安全）
  - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

Changed
- 初回リリースのため該当なし

Fixed
- 初回リリースのため該当なし

Security
- 認証トークン管理の注意:
  - jquants_client はリフレッシュトークンから id_token を取得するため、リフレッシュトークンの保護を厳格に行うこと
  - 自動 .env ロード機構は OS 環境変数をプロテクト（.env による上書きをデフォルトで抑制）する設計を採用

Known limitations / TODO
- strategy、execution、monitoring に関する具体的な実装は未実装（パッケージ構成のみ）
- quality モジュールは主要チェックを実装しているが、追加のチェックや閾値チューニングが想定される
- 監査モジュールはテーブル定義と初期化関数を提供するのみで、トランザクション単位の書き込みヘルパー等は今後の追加を検討
- エラー分類・通知（Slack 連携等）は Settings にトークンはあるが、実際の通知機能は別モジュールで実装が必要

Copyright
- 本 CHANGELOG はソースコードの内容から推測して作成したものであり、実際のコミットログとは異なる場合があります。必要に応じてプロジェクトの変更履歴（git log）やリリースノートに基づいて調整してください。