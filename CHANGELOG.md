CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。セマンティックバージョニングを採用しています。

[0.1.0] - 2026-03-15
-------------------

初期リリース — KabuSys 日本株自動売買システムの最初の公開バージョンです。

追加 (Added)
- パッケージ初期化
  - kabusys パッケージを追加。__version__ = "0.1.0" を設定。
  - サブパッケージとして data, strategy, execution, monitoring を公開。

- 環境設定管理 (src/kabusys/config.py)
  - Settings クラスを追加し、環境変数から設定を取得する共通 API を提供。
  - 必須設定の取得用ヘルパー _require を実装（未設定時は ValueError を投げる）。
  - サポートされる設定項目（例）:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live。デフォルト: development）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL。デフォルト: INFO）
  - 環境フラグ用の便利プロパティを追加: is_live, is_paper, is_dev。

- .env 自動ロード機能
  - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）に基づき .env/.env.local を自動読み込み（OS 環境変数優先）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env のパースは以下に対応:
    - export KEY=val 形式
    - シングル/ダブルクォートされた値（バックスラッシュによるエスケープ処理を考慮）
    - コメントの扱い（未クォート時の '#' は直前が空白またはタブの場合にコメントと認識）
  - OS 環境変数は protected として .env で上書きされない。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants の以下エンドポイントを扱う関数を実装:
    - fetch_daily_quotes: 日足（OHLCV）取得（ページネーション対応）
    - fetch_financial_statements: 四半期財務データ取得（ページネーション対応）
    - fetch_market_calendar: JPX マーケットカレンダー取得
  - 認証:
    - get_id_token(refresh_token=None): リフレッシュトークンから id_token を取得（POST /token/auth_refresh）。
    - モジュールレベルの id_token キャッシュを実装し、ページネーション間でトークンを共有。
    - 401 受信時は自動でトークンリフレッシュを試み、最大 1 回のみリトライ。
  - レート制御・リトライ:
    - 固定間隔スロットリングで API レート制限（既定 120 req/min）を順守する RateLimiter を実装。
    - ネットワークエラーや一部ステータス（408, 429, 5xx）に対する指数バックオフによるリトライ（最大 3 回）。
    - 429 の場合、Retry-After ヘッダを優先して待機時間を決定。
  - 取得時のトレーサビリティ:
    - Look-ahead bias を避けるため、save 系関数は fetched_at を UTC タイムスタンプで保存。

- DuckDB スキーマ (src/kabusys/data/schema.py)
  - DataSchema.md に準拠した 3 層（Raw / Processed / Feature）＋ Execution 層のテーブル群を定義。
  - 主なテーブル群（一部）:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型制約、CHECK、PRIMARY KEY、外部キーを付与。
  - 検索パフォーマンスを考慮したインデックスを複数定義（銘柄×日付、ステータス検索など）。
  - init_schema(db_path) を実装:
    - DuckDB ファイルの親ディレクトリを自動作成（":memory:" をサポート）
    - 全テーブル・インデックスを冪等に作成して DuckDB 接続を返す。
  - get_connection(db_path) を実装（既存 DB へ素直に接続）。

- DuckDB への保存ユーティリティ（jquants_client の save_*）
  - save_daily_quotes, save_financial_statements, save_market_calendar を実装。
  - INSERT ... ON CONFLICT DO UPDATE を用いた冪等保存を行う。
  - PK 欠損行はスキップし、その件数を警告ログに出力。
  - 型変換ユーティリティ _to_float / _to_int を提供:
    - _to_int は "1.0" のような float 文字列を許容するが、小数部が 0 以外の場合は None を返す（意図しない切り捨てを防止）。

- 監査ログ（Audit）モジュール (src/kabusys/data/audit.py)
  - トレーサビリティ用の監査テーブル群を追加:
    - signal_events（戦略が生成したシグナルの完全記録）
    - order_requests（発注要求、order_request_id を冪等キーとして扱う）
    - executions（証券会社からの約定情報）
  - 設計原則（ドキュメントに基づく）を反映:
    - すべての TIMESTAMP は UTC（init_audit_schema が SET TimeZone='UTC' を実行）
    - 削除しない監査設計（ON DELETE RESTRICT）
    - order_requests は order_type による CHECK（limit/stop の価格必須制約等）
    - ステータス遷移設計を反映（pending → sent → filled/… 等）
  - init_audit_schema(conn) / init_audit_db(db_path) を実装して既存接続または専用 DB に監査テーブルを追加可能。
  - 監査用のインデックスを複数定義（signal_id・日付・broker_order_id 等の高速検索を想定）。

変更 (Changed)
- なし（初回リリース）

修正 (Fixed)
- なし（初回リリース）

既知の制限・注意点 (Notes)
- strategy、execution、monitoring のパッケージは初期構成で空の __init__ を含み、実装は今後追加予定。
- .env の自動ロードはプロジェクトルート検出に依存するため、配布後やインストール環境では適宜 KABUSYS_DISABLE_AUTO_ENV_LOAD を利用するか、環境変数を明示的に設定してください。
- DuckDB スキーマは厳密な CHECK 制約を多用しています。既存データを移行する場合はデータ整形が必要になることがあります。

互換性の破壊 (Breaking Changes)
- なし（初回リリース）

開発者向けメモ (Developer Notes)
- jquants_client の _request は id_token の自動リフレッシュを行う設計のため、get_id_token 呼び出し内部から _request を呼ぶ場合は allow_refresh=False にして無限再帰を防ぐ必要がある（実装済み）。
- Save 系関数は DuckDB の executemany を利用して一括挿入し、ON CONFLICT で更新を行うため繰り返し実行しても冪等性が保たれます。
- 監査テーブルは削除されることを想定していないため、アプリケーション側で updated_at の適切な更新を行うこと（初期DDLに updated_at カラムを含める等）を忘れないでください。

作者
- 初期実装: KabuSys 開発チーム

（今後のリリースでは機能追加・パフォーマンス改善・戦略・発注エンジン統合等を記録していきます。）