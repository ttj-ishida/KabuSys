CHANGELOG
=========

すべての重要な変更点をここに記録します。フォーマットは "Keep a Changelog" に準拠しています。
リリースはセマンティックバージョニングに従っています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-15
--------------------

初回公開リリース。

Added
- パッケージ構成を追加
  - kabusys パッケージ（バージョン 0.1.0）
  - サブモジュール: data, strategy, execution, monitoring（strategy/execution/monitoring は初期プレースホルダ）
- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数からの設定自動読み込みを実装
    - プロジェクトルート検出: カレントワーキングディレクトリに依存せず、__file__ を起点に .git または pyproject.toml を探索
    - 読み込み順序: OS 環境変数 > .env.local > .env
    - OS 環境変数は保護され、.env によって上書きされない
    - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサ:
    - 空行・コメント行対応
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメントの取り扱い（クォートあり/なしでの挙動の差分）
  - Settings クラス: 環境変数からの取得プロパティを提供（必須キーは未設定時に ValueError を送出）
    - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - オプション/デフォルト:
      - KABU_API_BASE_URL: "http://localhost:18080/kabusapi"
      - KABUSYS_ENV: デフォルト "development"（有効値: development, paper_trading, live）
      - LOG_LEVEL: デフォルト "INFO"（有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL）
      - DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
      - SQLITE_PATH: デフォルト "data/monitoring.db"
    - ヘルパープロパティ: is_live, is_paper, is_dev
- J-Quants API クライアント (kabusys.data.jquants_client)
  - 取得対象:
    - 株価日足（OHLCV）
    - 財務データ（四半期 BS/PL）
    - JPX マーケットカレンダー（祝日・半日・SQ）
  - 機能:
    - レート制御: 固定間隔スロットリングで 120 req/min を保証（_RateLimiter）
    - 再試行ロジック: 指数バックオフ（最大 3 回）、対象ステータスコードは 408/429/5xx
      - 429 の場合は Retry-After ヘッダを優先
    - 認証トークン管理:
      - リフレッシュトークンから id_token を取得する get_id_token()
      - id_token のモジュールレベルキャッシュ（ページネーション間で共有）
      - 401 受信時は id_token を自動リフレッシュして最大 1 回リトライ（無限再帰防止のため allow_refresh フラグ）
    - ページネーション対応: fetch_* 関数は pagination_key を用いて全件取得
    - Look-ahead Bias 防止: データ保存時に fetched_at を UTC ISO 形式で記録
    - 保存関数（DuckDB への書き込み）:
      - save_daily_quotes, save_financial_statements, save_market_calendar を提供
      - 冪等性確保: INSERT ... ON CONFLICT DO UPDATE（主キー重複時は更新）
    - ユーティリティ変換関数:
      - _to_float: 変換失敗または空値は None
      - _to_int: "1.0" のような表現は許容（float 経由で小数部が 0 の場合のみ int に変換）、小数部がある場合は None を返す（意図しない切り捨て防止）
- DuckDB スキーマ (kabusys.data.schema)
  - 3 層アーキテクチャに基づくテーブル定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型、チェック制約、主キーを設定
  - 頻出クエリ向けのインデックス定義を追加（例: code×date, status 検索など）
  - init_schema(db_path) による初期化関数を提供（親ディレクトリ自動作成、冪等）
  - get_connection(db_path) で既存 DB への接続を返す（初期化は行わない）
- 監査ログ（トレーサビリティ） (kabusys.data.audit)
  - 監査用テーブルの定義と初期化:
    - signal_events（シグナル生成ログ）
    - order_requests（発注要求ログ、order_request_id を冪等キーとして定義）
      - order_type に応じた CHECK（limit/stop/market の価格必須・不要のルール）
    - executions（約定ログ、broker_execution_id をユニーク冪等キーとして扱う）
  - 監査用インデックスを定義（signal_events の日付・銘柄検索、order_requests のステータス検索など）
  - init_audit_schema(conn) で既存接続へ監査テーブルを追加（すべての TIMESTAMP は UTC に設定）
  - init_audit_db(db_path) による監査専用 DB 初期化を提供
- DuckDB 初期化時の運用注記
  - audit 初期化では "SET TimeZone='UTC'" を実行し、TIMESTAMP を UTC 保存する方針

Changed
- 初回リリースのため該当なし

Fixed
- 初回リリースのため該当なし

Security
- 初期リリースにおいて、認証トークン（J-Quants refresh token 等）は環境変数で管理する設計。ソースにハードコードしないことを推奨。

Notes / Migration
- 初回リリースの DB 初期化手順:
  - data.schema.init_schema(settings.duckdb_path) を呼び出して基本スキーマを作成
  - 必要に応じて data.audit.init_audit_schema(conn) を呼び出して監査テーブルを追加
- 環境変数の自動読み込みはプロジェクトルートの検出に依存するため、配布後やテスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを無効にしてください。
- J-Quants API の利用には JQUANTS_REFRESH_TOKEN が必要です。トークン管理とリフレッシュはクライアント側で自動化されていますが、リフレッシュ用のリフレッシュトークン自体は安全に保管してください。

Authors
- 初期実装チーム（コードベースから推測）：KabuSys 開発チーム

---- 

（この CHANGELOG はリポジトリの現在のコードベースから推測して作成しています。実際のコミット履歴やリリースノートがある場合はそちらに基づいて更新してください。）