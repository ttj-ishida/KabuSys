Keep a Changelog
===============

すべての重要な変更はこのファイルに記録します。  
このファイルは "Keep a Changelog" の指針に従っています。  
https://keepachangelog.com/ja/1.0.0/

すべてのバージョンはセマンティックバージョニングに従います。

0.1.0 - 2026-03-16
-----------------

Added
- 初回公開: 日本株自動売買ライブラリ「kabusys」基本モジュール群を追加。
  - パッケージ情報
    - パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)
    - __all__ に data, strategy, execution, monitoring をエクスポート（strategy/execution/monitoring は入れ物を提供）
  - 環境設定管理 (src/kabusys/config.py)
    - .env または環境変数からの自動読み込み機能（プロジェクトルートを .git / pyproject.toml で探索）
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
    - .env パーサ: export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント等に対応
    - 必須設定取得ヘルパー _require()（未設定時は ValueError を送出）
    - Settings クラス: J-Quants、kabu API、Slack、DB パス、環境（development/paper_trading/live）、ログレベル等のプロパティを提供
    - デフォルト値: KABU_API_BASE_URL="http://localhost:18080/kabusapi", DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
    - バリデーション: KABUSYS_ENV と LOG_LEVEL の有効値チェック
  - J-Quants API クライアント (src/kabusys/data/jquants_client.py)
    - prices daily_quotes、financial statements（四半期 BS/PL）、markets trading_calendar を取得する fetch_* 関数を提供
    - ページネーション対応（pagination_key を用いた繰り返し取得）
    - レート制限: 固定間隔スロットリングで 120 req/min（_RateLimiter）
    - リトライロジック: 指数バックオフ（base=2s）、最大 3 回、対象ステータス 408/429/5xx、429 の場合は Retry-After を優先
    - 401 発生時はリフレッシュ（get_id_token）して 1 回だけ再試行（無限再帰を防止）
    - id_token キャッシュによる効率化（ページネーション間で共有）
    - JSON デコード失敗での詳細エラーメッセージ
    - データ保存関数 save_*(): DuckDB へ冪等に保存（ON CONFLICT DO UPDATE）、fetched_at を UTC ISO8601 で記録
    - 型変換ユーティリティ _to_float / _to_int（安全な変換ロジック）
  - DuckDB スキーマ管理 (src/kabusys/data/schema.py)
    - Raw / Processed / Feature / Execution 層を想定した DDL を定義
    - 主要テーブル（例: raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, signal_queue, orders, trades, positions, portfolio_performance など）を作成
    - 適切な制約（PRIMARY KEY / CHECK / FOREIGN KEY）およびインデックスを定義
    - init_schema(db_path) でデータベースと全テーブルを冪等に初期化（":memory:" サポート）
    - get_connection(db_path) で既存 DB に接続（初期化は行わない）
  - ETL パイプライン (src/kabusys/data/pipeline.py)
    - 日次 ETL run_daily_etl()：市場カレンダー→株価日足→財務データ→品質チェック の順で差分取得・保存・品質チェックを実行
    - 差分更新ロジック: DB の最終取得日から未取得範囲のみ取得、デフォルトのバックフィル日数は 3 日（後出し修正を吸収）
    - 市場カレンダーは先読み（デフォルト 90 日）して営業日判定に利用
    - 各ステップは独立してエラーハンドリング（1ステップ失敗でも他ステップ継続）、結果を ETLResult で返却（品質問題やエラーの集合を保持）
    - テスト容易性のため id_token を注入可能
  - 監査ログ (src/kabusys/data/audit.py)
    - strategy → signal → order_request → executions を追跡する監査用テーブルを追加
    - signal_events, order_requests, executions の DDL とインデックスを提供
    - init_audit_schema(conn) で既存接続に監査テーブルを追加（UTC タイムゾーン固定）
    - init_audit_db(db_path) で監査専用 DB を初期化可能
    - 冪等キー（order_request_id, broker_execution_id 等）や created_at/updated_at の運用方針を明文化
  - データ品質チェック (src/kabusys/data/quality.py)
    - check_missing_data(): raw_prices の OHLC 欠損検出（サンプル最大 10 件を返す）
    - check_spike(): 前日比でのスパイク検出（デフォルト閾値 50%）
    - QualityIssue データクラスによる問題報告（check_name, table, severity, detail, rows）
    - 各チェックは全件収集方式（Fail-Fast ではない）で呼び出し元で重大度に応じた判断を可能にする

Changed
- （新規リリースのため該当なし）

Fixed
- （新規リリースのため該当なし）

Deprecated
- （新規リリースのため該当なし）

Removed
- （新規リリースのため該当なし）

Security
- 機密情報（J-Quants リフレッシュトークン、kabu API パスワード、Slack トークン等）は環境変数で管理することを想定。Settings._require() は未設定時に明確にエラーを投げる。
- .env 読み込みは既存 OS 環境変数を保護する（override ロジック）し、KABUSYS_DISABLE_AUTO_ENV_LOAD により CI/テストで自動ロードを抑止可能。

Notes / 使用上のポイント
- 必須環境変数（例）
  - JQUANTS_REFRESH_TOKEN（J-Quants 用リフレッシュトークン）
  - KABU_API_PASSWORD（kabuステーション API パスワード）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（監視通知用）
- 設定関連
  - KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれか（大小文字不問、内部で lower()）
  - LOG_LEVEL は "DEBUG","INFO","WARNING","ERROR","CRITICAL" のいずれか
  - デフォルトの J-Quants ベース URL は https://api.jquants.com/v1、KabuAPI のデフォルトは http://localhost:18080/kabusapi
- DB 初期化
  - データ層: schema.init_schema(settings.duckdb_path) を実行してテーブルを作成
  - 監査層: init_audit_schema(conn) または init_audit_db() を使用
  - ":memory:" を渡すとインメモリ DB を使用可能
- ETL 実行
  - run_daily_etl(conn, target_date=None) を呼ぶと市場カレンダー→株価→財務→品質チェックを順に実行し ETLResult を返す
  - ETLResult.to_dict() → 品質問題は (check_name, severity, message) の形式で取得可能
- リトライ/レート制御
  - J-Quants API は 120 req/min に合わせて固定間隔スロットリングを実装（内部で sleep）
  - ネットワーク障害や HTTP 408/429/5xx に対する自動リトライを行う（最大 3 回）
  - 401 は 1 回だけトークンをリフレッシュして再試行する（それでも 401 の場合はエラー）
- 現状の機能範囲
  - データ取得・保存・品質チェック・監査ログ基盤を提供
  - strategy / execution / monitoring モジュールはパッケージ構成として存在するが、発注ロジックや戦略実装・監視ロジックは本リリースでは未実装（拡張ポイントとして意図）
- 依存関係（実行に必要）
  - Python 標準ライブラリ（urllib 等）に加え duckdb が必須

既知の制約 / 将来の改善候補
- J-Quants クライアントは urllib を使用しているため、高度な HTTP 機能（セッション管理、接続プール等）は限定的。将来的に requests / httpx などへの移行検討があり得る。
- スロットリングは固定間隔スロットリングのため、burst を許容する仕様にはなっていない（API レート制限厳守を優先）。
- strategy / execution の具体的な発注処理・ブローカー連携は今後の拡張対象。
- 品質チェックの種類は増強予定（ニュース整合性、財務の時間的矛盾チェック等）。

アップグレード手順
- 新規プロジェクト向け初期セットアップ:
  1. 必要な環境変数を設定（またはプロジェクトルートに .env/.env.local を用意）
  2. duckdb スキーマを初期化: from kabusys.data.schema import init_schema; init_schema(settings.duckdb_path)
  3. 監査ログが必要であれば init_audit_schema(conn) を呼ぶ
  4. run_daily_etl() を定期実行してデータ収集を開始

問い合わせ / 貢献
- バグ報告・機能要望はリポジトリの Issue に記載してください。README や DataPlatform.md / DataSchema.md に沿って実装・テストを追加していただけると助かります。