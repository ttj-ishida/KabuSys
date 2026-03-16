CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
リリースの安定度はセマンティックバージョニングに従います。

0.1.0 - 2026-03-16
------------------

Added
- 初回リリース。日本株自動売買システム「KabuSys」の基盤機能を実装。
  - パッケージ構成
    - kabusys (パッケージエントリ; __version__ = 0.1.0)
    - サブパッケージ: data, strategy, execution, monitoring（骨組みを提供）
  - 環境設定（kabusys.config）
    - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
      - 読み込み順: OS 環境変数 > .env.local > .env
      - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
      - プロジェクトルート判定は __file__ を起点に .git または pyproject.toml を探索（配布後も動作）
    - .env パーサの実装（_parse_env_line）
      - コメント行、export プレフィックス、シングル/ダブルクォート、エスケープシーケンスを考慮
      - クォートなしの行では '#' が直前にスペース/タブある場合をコメントとみなす挙動
    - .env 読み込み関数（_load_env_file）
      - override と protected オプションによる既存 OS 環境変数保護
    - Settings クラス（settings インスタンス）
      - J-Quants / kabustation / Slack / DB（DuckDB/SQLite） / システム設定をプロパティで提供
      - 必須値取得時には _require により未設定で ValueError を送出
      - KABUSYS_ENV の値検証（development / paper_trading / live）
      - LOG_LEVEL の値検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
      - is_live / is_paper / is_dev の利便性プロパティ
  - J-Quants API クライアント（kabusys.data.jquants_client）
    - 提供データ: 日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー
    - レート制限機構
      - 固定間隔スロットリング実装 (120 req/min を想定)
    - リトライ・耐障害性
      - 指数バックオフ、最大リトライ回数 3 回（ネットワーク系エラー・HTTP 408/429/5xx 対象）
      - 429 の場合は Retry-After ヘッダを優先
      - 401 受信時はトークンを自動リフレッシュして 1 回リトライ（無限再帰防止のため allow_refresh フラグ）
    - トークンキャッシュ
      - モジュールレベルの ID トークンキャッシュを共有（ページネーション間での再利用）
    - ページネーション対応の取得関数
      - fetch_daily_quotes / fetch_financial_statements: pagination_key を用いた繰り返し取得と重複防止
      - fetch_market_calendar: マーケットカレンダー取得
    - DuckDB 連携保存関数（冪等）
      - save_daily_quotes / save_financial_statements / save_market_calendar
      - ON CONFLICT DO UPDATE を用いた冪等書き込み
      - fetched_at を UTC ISO8601 で記録（look-ahead bias 対策のため取得時刻を保存）
      - 主キー欠損行をスキップして警告ログを出す実装
    - ユーティリティ
      - 型変換関数 _to_float / _to_int（不正値は None に正しく落とす。_to_int は小数部チェックを実施）
  - データベーススキーマ（kabusys.data.schema）
    - DuckDB 用のスキーマ DDL を定義（Raw / Processed / Feature / Execution 層）
      - Raw 層: raw_prices, raw_financials, raw_news, raw_executions
      - Processed 層: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - Feature 層: features, ai_scores
      - Execution 層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 各テーブルに制約（PRIMARY KEY, CHECK など）を付与してデータ整合性を強化
    - 頻出クエリ向けにインデックスを作成（コード＋日付やステータス検索など）
    - init_schema(db_path) による初期化関数
      - 親ディレクトリ自動作成（ファイルベース DB の場合）、":memory:" サポート
      - DDL を冪等的に適用して接続を返す
    - get_connection(db_path) による既存 DB への接続取得（スキーマ初期化は行わない）
  - 監査ログ（kabusys.data.audit）
    - シグナルから約定に至る監査用テーブル群（signal_events, order_requests, executions）
    - トレーサビリティ設計（UUID 連鎖：strategy_id → signal_id → order_request_id → broker_order_id）
    - order_request_id を冪等キーとして再送制御を想定
    - 全 TIMESTAMP を UTC で保存する（init_audit_schema は SET TimeZone='UTC' を実行）
    - init_audit_schema(conn) / init_audit_db(db_path) による初期化 API
    - インデックス群による検索性能チューニング（status、signal_id、broker_order_id、executed_at 等）
  - データ品質チェック（kabusys.data.quality）
    - DataPlatform に基づく品質チェック実装
      - 欠損データ検出（open/high/low/close の欠損）
      - 異常値（スパイク）検出（前日比の絶対変動率閾値で判定、デフォルト 50%）
      - 重複チェック（主キー重複）
      - 日付不整合チェック（未来日付・market_calendar と矛盾する非営業日データ）
    - QualityIssue dataclass による問題表現（check_name, table, severity, detail, rows）
    - 各チェックは問題をすべて収集して返す（Fail-Fast ではない）
    - SQL をパラメータバインドで実行し、DuckDB 上で効率的に集計
    - run_all_checks 関数で一括実行し、ログで要約（error/warning 件数）
  - その他
    - 監視用パッケージ骨子 (kabusys.monitoring) と strategy/execution パッケージ（初期化ファイルのみ）

Notes / Usage
- 環境変数で必須の値を設定してください（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。未設定時は Settings の対応プロパティで ValueError を発生させます。
- J-Quants のトークン取得は get_id_token() を使用。_request は 401 で自動リフレッシュを行いますが、get_id_token 内呼び出しでは無限再帰を避けるため allow_refresh=False を渡しています。
- DuckDB スキーマ初期化は init_schema() を一度呼び出してください。監査ログは既存接続に対して init_audit_schema() で追加できます。
- データ品質チェックは ETL の各段階で run_all_checks を呼び出し、返却された QualityIssue を基に処理継続/停止を判断してください。

Known limitations / TODO
- strategy / execution / monitoring の実装は骨子レベル（具体的な戦略ロジックや注文送信実装は未実装）。
- 外部 API 呼び出しのテスト用フックやモック機構は未整備（ユニットテストのためには環境変数で自動ロードを無効化するなどの対策が必要）。
- DuckDB の UNIQUE / 外部キーの動作や NULL 扱いに関する振る舞いは実運用での検証が必要。

--- 

（今後のリリースでは bugfix / changed / deprecated / removed / security セクションを用いて差分を分かりやすく記載します。）