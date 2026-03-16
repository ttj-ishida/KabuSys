CHANGELOG
=========

すべての notable な変更は Keep a Changelog の形式で記載しています。
https://keepachangelog.com/ja/

[Unreleased]

0.1.0 - 2026-03-16
------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムの基盤モジュール群を追加。
  - パッケージ初期化
    - src/kabusys/__init__.py
      - __version__ = "0.1.0"
      - パブリックAPIとして data, strategy, execution, monitoring を公開。
  - 設定・環境変数管理
    - src/kabusys/config.py
      - .env ファイルまたは OS 環境変数から設定を自動読み込み（優先順位: OS 環境 > .env.local > .env）。
      - プロジェクトルートを .git または pyproject.toml から検出するロジック（パッケージ配布後でも動作）。
      - .env 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用）。
      - export KEY=val 形式やクォート/エスケープ、行末コメントのパースに対応する堅牢な .env パーサを実装。
      - 必須環境変数取得時の _require() による明示的エラー（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）。
      - 環境変数値の検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と便利なプロパティ（is_live 等）。
  - データ取得クライアント（J-Quants）
    - src/kabusys/data/jquants_client.py
      - J-Quants API から日次株価（OHLCV）、四半期財務、JPX マーケットカレンダーを取得するクライアントを追加。
      - レート制限（120 req/min）を守る固定間隔スロットリング(_RateLimiter) を実装。
      - HTTP リトライ（指数バックオフ、最大3回）、408/429/5xx の再試行、429 の Retry-After 優先処理を実装。
      - 401 受信時の自動トークンリフレッシュ（1 回のみ）と id_token のモジュールキャッシュをサポート。
      - ページネーション対応（pagination_key を追跡）。
      - Look-ahead bias を防ぐため取得時刻 fetched_at を UTC で付与。
      - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）は冪等（ON CONFLICT DO UPDATE）で実装。
      - 型変換ユーティリティ(_to_float, _to_int) で不正値を安全に扱う。
  - DuckDB スキーマ定義
    - src/kabusys/data/schema.py
      - Raw / Processed / Feature / Execution の 3 層（+ Execution/Audit 層）に対応したテーブル定義を追加。
      - raw_prices, raw_financials, raw_news, raw_executions など Raw レイヤーのDDLを定義。
      - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed レイヤーDDLを定義。
      - features, ai_scores を含む Feature レイヤーDDLを定義。
      - signals, signal_queue, orders, trades, positions, portfolio_performance など Execution レイヤーDDLを定義。
      - パフォーマンス/利用頻度に応じたインデックス定義を追加。
      - init_schema(db_path) により自動でディレクトリ作成・テーブル作成を行い DuckDB 接続を返すユーティリティを提供。
      - get_connection(db_path) により既存DBへ接続可能（初期化は行わない）。
  - ETL パイプライン
    - src/kabusys/data/pipeline.py
      - 日次 ETL 実行エントリ run_daily_etl を実装（カレンダー→株価→財務→品質チェックの順）。
      - run_prices_etl / run_financials_etl / run_calendar_etl といった差分更新ジョブを提供。差分計算・backfill（日数指定）・営業日調整をサポート。
      - ETLResult データクラスで取得件数・保存件数・品質問題・エラー概要を収集して返す（監査・ロギング用途）。
      - 市場カレンダーの先読み（デフォルト 90 日）や株価/財務のデフォルトバックフィル（デフォルト 3 日）など運用に配慮した既定値を設定。
      - 各ステップは例外ハンドリングされ、1 ステップ失敗でも他ステップは継続して実行（Fail-Fast ではない挙動）。
      - 品質チェックは外部モジュールと連携して実行可能（run_quality_checks フラグ）。
  - 監査ログ（トレーサビリティ）
    - src/kabusys/data/audit.py
      - 戦略→シグナル→発注要求→約定 の一連の監査ログテーブル(signal_events, order_requests, executions) を追加。
      - order_request_id を冪等キーとする設計、すべてのテーブルに created_at/updated_at を付与。
      - DuckDB の TimeZone を UTC に固定してタイムスタンプを扱う仕様（init_audit_schema で SET TimeZone='UTC' を実行）。
      - init_audit_db(db_path) により監査用 DB を初期化して接続を返すユーティリティを提供。
      - 監査用インデックスを多数追加（status 検索、signal_id/日付での検索など）。
  - データ品質チェック
    - src/kabusys/data/quality.py
      - QualityIssue データクラスを追加（check_name, table, severity, detail, rows を保持）。
      - check_missing_data: raw_prices の OHLC 欠損（open/high/low/close）を検出。サンプル行を最大 10 件返す。
      - check_spike: LAG ウィンドウで前日比のスパイク（デフォルト 50%）を検出し、サンプル行を返す。
      - SQL パラメタバインドで効率的かつ安全に DuckDB 上でチェックを実施。
  - API/テスト利便性
    - id_token を外部から注入できる設計によりユニットテスト容易性を確保（jquants_client.fetch_* / pipeline 系）。
    - DuckDB の ":memory:" を使ったインメモリ初期化をサポート。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / 運用メモ
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などが _require() により必須扱いになる。
  - .env.example を参照して .env を作成してください。
- .env 自動ロード:
  - デフォルトでパッケージ読み込み時にプロジェクトルートの .env/.env.local を自動読み込みします。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
- DuckDB 初期化:
  - init_schema() は親ディレクトリ自動作成を行います。":memory:" を指定するとインメモリ DB を使用できます。
- タイムゾーン:
  - 監査ログは明示的に SET TimeZone='UTC' を実行し、UTC タイムスタンプで保存します。
- レート制限・リトライ:
  - J-Quants へのリクエストは 120 req/min の制限を尊重する必要があります。ライブラリは固定間隔スロットリングとリトライを実装していますが、運用上の追加制御は必要に応じて検討してください。

Known issues
- なし（初回リリース）。運用中に検出された問題は以降のバージョンで追記します。