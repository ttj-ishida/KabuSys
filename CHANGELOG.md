Keep a Changelog に準拠した CHANGELOG.md（日本語）を以下に作成しました。リポジトリ内のコードから推測して記載しています。

CHANGELOG.md
-------------

全般的な注意
- このファイルは Keep a Changelog の形式に従っています。
- バージョン番号は src/kabusys/__init__.py の __version__ を参照しています。
- 日付はコード解析時点（日付: 2026-03-16）を使用しています（実際のリリース日があれば適宜置換してください）。

Unreleased
----------
- なし

0.1.0 - 2026-03-16
------------------
Added
- パッケージ初期リリース: kabusys (バージョン 0.1.0)
  - パッケージトップ: src/kabusys/__init__.py により data, strategy, execution, monitoring の公開を定義。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートの検出: .git または pyproject.toml を基準に探索（CWD に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能（テスト向け）。
  - .env パーサ: export 形式、クォートされた値・エスケープ、インラインコメントの取り扱いなどに対応。
  - Settings クラスでアプリケーション設定をプロパティとして提供:
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
    - DB パスのデフォルト（DUCKDB_PATH, SQLITE_PATH）。
    - KABUSYS_ENV・LOG_LEVEL の値検証（有効値を列挙）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- J‑Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 株価日足、財務データ（四半期 BS/PL）、JPX 市場カレンダーを取得する fetch_* 関数を実装。
  - HTTP ユーティリティ:
    - 固定間隔のレートリミッタ（120 req/min を厳守）。
    - 再試行ロジック（指数バックオフ、最大 3 回、対象ステータス: 408/429/5xx）。
    - 401 受信時はリフレッシュして 1 回リトライ（トークン自動更新）。
    - ページネーション対応（pagination_key の追跡）。
    - JSON デコードエラーやタイムアウト等の扱い。
  - get_id_token: リフレッシュトークンから idToken を取得する POST 実装。
  - DuckDB への保存関数 save_*:
    - save_daily_quotes / save_financial_statements / save_market_calendar。
    - 冪等性: INSERT ... ON CONFLICT DO UPDATE を使用して重複を排除。
    - fetched_at を UTC タイムスタンプで記録し、Look-ahead バイアスのトレースを可能に。
    - PK 欠損行はスキップしてログ出力。

- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - 3 層（Raw / Processed / Feature）+ Execution 層のテーブル定義を実装。
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - インデックス定義（典型的なクエリパターンに基づく）。
  - init_schema(db_path) により DB ファイルの親ディレクトリを自動作成して全テーブル／インデックスを作成（冪等）。
  - get_connection(db_path) を提供。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 日次 ETL のエントリポイント run_daily_etl を実装。
    - 処理フロー: カレンダー ETL → 株価 ETL → 財務 ETL → 品質チェック（オプション）。
    - 各ステップは個別に例外を捕捉し、1 ステップの失敗が他を停止させない設計。
  - 個別ジョブ:
    - run_calendar_etl (カレンダー先読み、デフォルト先読み 90 日)
    - run_prices_etl (差分更新、バックフィルデフォルト 3 日)
    - run_financials_etl (差分更新、バックフィル)
  - 差分更新支援:
    - テーブルの最終取得日を取得するユーティリティ（get_last_price_date 等）。
    - 非営業日を最近の営業日に調整する _adjust_to_trading_day（market_calendar を参照）。
  - ETLResult データクラスで実行結果・品質問題・エラーを収集して返却。
  - quality モジュールとの連携（品質チェックを実行）。

- 監査ログ（トレーサビリティ）(src/kabusys/data/audit.py)
  - 監査用テーブルを別モジュールとして実装:
    - signal_events（戦略が生成したシグナルのログ）
    - order_requests（冪等キー order_request_id を持つ発注要求ログ）
    - executions（証券会社からの約定ログ、broker_execution_id を冪等キーとして扱う）
  - インデックスと外部キー（ON DELETE RESTRICT）を定義。
  - init_audit_schema(conn), init_audit_db(db_path) を提供。
  - 全ての TIMESTAMP は UTC 保存（init 時に SET TimeZone='UTC' を実行）。
  - ステータス遷移とチェック制約を設計に組み込む（limit/stop/market の価格要件など）。

- データ品質チェック (src/kabusys/data/quality.py)
  - QualityIssue データクラスを定義（チェック名・テーブル・重大度・詳細・サンプル行）。
  - 実装済みチェック（代表）:
    - check_missing_data: raw_prices の必須カラム（open/high/low/close）欠損検出（重大度 error）。
    - check_spike: 前日比でのスパイク検出（LAG ウィンドウを使用、デフォルト閾値 50%）。
  - 各チェックはサンプル行を返し、Fail-Fast ではなく全件収集する設計。
  - DuckDB 上で SQL を実行して効率的に判定（パラメータバインド使用）。

- ETL 品質ワークフロー設計文書（コード内ドキュメント）
  - 各モジュールに設計原則（レート制限、リトライ、冪等性、トレーサビリティ、UTC 保存など）をコメントで明記。

- 依存関係・実行環境
  - DuckDB を用いる実装（duckdb.connect を使用）。
  - 標準ライブラリ urllib を用いた HTTP クライアント実装（リトライ・ヘッダ処理を自前実装）。
  - ロギングを各処理で行う（logger を利用）。

Changed
- 初版リリースのため該当なし。

Fixed
- 初版リリースのため該当なし。

Deprecated
- 初版リリースのため該当なし。

Removed
- 初版リリースのため該当なし。

Security
- 初版リリースのため該当なし。

Notes / Known limitations
- strategy および execution パッケージは __init__.py のみ（プレースホルダ）。実際の戦略ロジック・発注実装は未実装。
- jquants_client は urllib を用いた実装であり、高度な HTTP クライアント（例: requests, httpx）への置換余地がある。
- テストコードや CI 設定はリポジトリからは確認できないため、ユニットテストや統合テストは別途整備が必要。
- 実稼働前に必須環境変数（JQUANTS_REFRESH_TOKEN 等）の設定と DuckDB スキーマ初期化（init_schema）を推奨。
- Save 関数は DuckDB のスキーマ（テーブル定義）に依存するため、スキーマ変更時は移行手順が必要。

移行・導入手順（簡易）
1. 必須環境変数を設定: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等。
2. init_schema(settings.duckdb_path) を呼び出して DuckDB を初期化。
3. run_daily_etl(conn) を呼んで初回ロード（大量データが必要なら backfill の調整）。
4. strategy / execution 実装を追加して監査ログを利用。

その他
- 実際のリリース時は日付の確認・必要なら "Unreleased" セクションの追加や項目の詳細化を行ってください。