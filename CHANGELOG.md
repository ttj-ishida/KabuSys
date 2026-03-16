CHANGELOG
=========
すべての変更は Keep a Changelog に準拠しています。  
このファイルは、リポジトリの現時点のコードベース（初期リリース相当）から推測して作成した変更履歴です。

0.1.0 - 初期リリース
-------------------

リリース日: 未指定

Added
- パッケージ基盤
  - kabusys パッケージの初期化。バージョンを 0.1.0 として設定。
  - パッケージの主要サブモジュールをエクスポート: data, strategy, execution, monitoring。

- 環境変数/設定管理 (kabusys.config)
  - .env ファイルまたは環境変数からの設定読み込み機能を実装。
  - プロジェクトルート自動検出（.git または pyproject.toml を起点に探索）により、CWD に依存しない自動 .env 読み込みをサポート。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - .env パーサ実装: export プレフィックス, シングル/ダブルクォート、バックスラッシュエスケープ、行末コメントの取り扱い等に対応。
  - Settings クラスを提供し、必須設定の取得（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）・既定値（KABU_API_BASE_URL, DB パスなど）・値検証（KABUSYS_ENV, LOG_LEVEL）を行う。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 呼び出しユーティリティを実装（JSON パース、タイムアウト設定）。
  - 固定間隔のレートリミッタ実装（デフォルト 120 req/min に準拠）。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。429 の場合は Retry-After を尊重。
  - 401 応答時の自動トークンリフレッシュ（1 回のみ）を実装。トークンはモジュールレベルでキャッシュ。
  - ページネーション対応のデータ取得関数:
    - fetch_daily_quotes（株価日足: OHLCV）
    - fetch_financial_statements（財務データ: 四半期 BS/PL）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB に対する冪等保存関数（ON CONFLICT DO UPDATE）:
    - save_daily_quotes -> raw_prices
    - save_financial_statements -> raw_financials
    - save_market_calendar -> market_calendar
  - データ型変換ユーティリティ (_to_float / _to_int) と取得時刻（fetched_at）を UTC で記録する設計（Look-ahead bias の抑制）。

- DuckDB スキーマ定義 (kabusys.data.schema)
  - DataPlatform の 3 層（Raw / Processed / Feature）＋Execution 層 を反映したテーブル定義を追加。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型制約・CHECK・PRIMARY KEY を設定。
  - 頻出クエリに備えたインデックスを定義。
  - init_schema(db_path) により DB ファイルの親ディレクトリを自動作成して全テーブル／インデックスを冪等的に作成。
  - get_connection(db_path) を提供（既存 DB への接続用）。

- ETL パイプライン (kabusys.data.pipeline)
  - 日次 ETL の主要フローを実装:
    1. 市場カレンダー ETL（先読み: デフォルト 90 日）→ 営業日調整に利用
    2. 株価日足 ETL（差分更新 + バックフィル: デフォルト 3 日）
    3. 財務データ ETL（差分更新 + バックフィル）
    4. 品質チェック（オプション）
  - 差分更新ロジック: DB 内の最終取得日を基に差分のみ取得、未取得時は J-Quants 提供開始日から取得。
  - backfill_days による再取得（後出し修正吸収）。
  - pagination や id_token 注入によりテスト容易性を確保。
  - ETLResult データクラスを追加（取得数・保存数・品質問題・エラー等を集約）。品質問題は (check_name, severity, message) 形式でシリアライズ可能。
  - run_daily_etl() を公開し、各ステップを独立して実行・例外を捕捉して他ステップへ影響を与えない設計。

- 監査ログ（トレーサビリティ） (kabusys.data.audit)
  - シグナル→発注→約定までトレースする監査テーブル群を追加:
    - signal_events（戦略が生成したシグナルのログ）
    - order_requests（発注要求、order_request_id を冪等キーとして扱う）
    - executions（証券会社からの約定ログ、broker_execution_id をユニークとして冪等）
  - すべての TIMESTAMP は UTC で保存する方針（init_audit_schema は SET TimeZone='UTC' を実行）。
  - ステータス列や制約（limit/stop 注文の price 必須チェック等）を設け、監査証跡の整合性を確保。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供。インデックスも追加。

- データ品質チェック (kabusys.data.quality)
  - QualityIssue データクラスを導入（check_name, table, severity, detail, rows）。
  - 実装済みチェック例:
    - check_missing_data: raw_prices の OHLC 欠損を検出（必須カラムの NULL をエラーとして検出、サンプル最大 10 件を返す）。
    - check_spike: LAG ウィンドウを用いて前日比のスパイク（デフォルト閾値 50%）を検出し、異常レコードを報告。
  - 設計方針として Fail-Fast を採らず、全チェックから問題リストを収集して呼び出し元が重大度に応じて判断できるようにしている。
  - DuckDB 接続を受け SQL で効率的に検査し、パラメータバインド (?) を使用してインジェクションリスクを軽減。

Changed
- （初期リリースのため無し）

Fixed
- （初期リリースのため無し）

Deprecated
- （初期リリースのため無し）

Removed
- （初期リリースのため無し）

Security
- 外部への HTTP 通信はトークン認証を前提。トークンは設定（JQUANTS_REFRESH_TOKEN）から取得してキャッシュする設計。
- .env の自動読み込みは必要に応じて環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Notes / 設計上のポイント（要約）
- 冪等性: API から取得したデータは DuckDB に対して ON CONFLICT DO UPDATE を用いて保存することで、再実行や重複取得に耐性を持たせている。
- レート制限と堅牢性: J-Quants API はレート制限（120 req/min）を守るための固定間隔レートリミッタを導入。リトライとトークン自動リフレッシュも組み込まれている。
- 時刻とトレーサビリティ: すべての監査用 TIMESTAMP/取得時刻は UTC で記録し、いつシステムがデータを取得したかを追跡可能にしている。
- データ品質: ETL の最後に品質チェックを実行してデータの欠損・スパイク等を検出し、運用側がアクションを判断できる情報を提供する。

今後の想定改善点（暗黙の依存・未実装箇所）
- quality モジュールにおける「重複チェック」「日付不整合チェック」等の追加実装や、run_all_checks の外部公開インターフェース整備（pipeline が run_all_checks を呼んでいるため、完全実装が前提）。
- strategy / execution / monitoring サブパッケージの具体的な実装（現在はパッケージプレースホルダ）。
- エラーハンドリング・監視（Slack 通知等）を結び付けるオペレーション用の導線（設定は存在するが、通知ロジックは本コードベースで未確認）。

参考
- データベース既定パス: DuckDB -> data/kabusys.duckdb、SQLite -> data/monitoring.db などを Settings で指定可能（環境変数で上書き可）。
- API ベース URL: デフォルトは http://localhost:18080/kabusapi（環境変数で上書き可）。

以上。必要であれば各モジュールごとの詳細な変更ログ（関数・DDL 列挙など）や英語版 CHANGELOG の作成も対応します。