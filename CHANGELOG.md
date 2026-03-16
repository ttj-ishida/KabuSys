# CHANGELOG

すべての重要な変更はこのファイルに記録します。本プロジェクトは Keep a Changelog のガイドラインに準拠します。

現在のバージョン: 0.1.0

---

## [0.1.0] - 初回リリース
最初の公開バージョン。以下の主要機能・モジュールを追加しました。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージを追加。__version__ = 0.1.0 を設定し、主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から探索して判断）。
  - .env の自動読み込みの挙動:
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
    - OS 環境変数は保護（.env による上書きを防ぐ）
  - .env パーサーは以下に対応:
    - 空行・コメント行（#）の無視
    - export KEY=val 形式の対応
    - シングル/ダブルクォートを含む値のパース（バックスラッシュエスケープ対応）
    - インラインコメントの取り扱い（クォート有りは無視、クォート無しは '#' の直前が空白/タブの場合にコメントとみなす）
  - Settings クラスを実装し、主要設定をプロパティ経由で取得:
    - J-Quants / kabu API / Slack / データベースパス（デフォルト: DUCKDB_PATH=data/kabusys.duckdb, SQLITE_PATH=data/monitoring.db）等
    - KABUSYS_ENV（development, paper_trading, live）のバリデーション
    - LOG_LEVEL（DEBUG, INFO, WARNING, ERROR, CRITICAL）のバリデーション
    - is_live / is_paper / is_dev の簡易判定プロパティ

- J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API から以下を取得する関数を提供:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（四半期財務、ページネーション対応）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - 認証ヘルパー:
    - get_id_token(refresh_token=None)：リフレッシュトークンから ID トークンを取得（POST）
    - モジュールレベルの ID トークンキャッシュを実装（ページネーション間で共有）
  - HTTP リクエストの堅牢化:
    - API レート制限を厳守する固定間隔スロットリング（120 req/min、_RateLimiter）
    - 再試行ロジック（指数バックオフ、最大 3 回、対象 408/429/5xx、429 の Retry-After を尊重）
    - 401 受信時はトークンを自動リフレッシュして一度だけリトライ（無限再帰防止のため allow_refresh フラグ）
    - JSON デコードエラーは明示的に報告
  - DuckDB 保存用ユーティリティ:
    - save_daily_quotes / save_financial_statements / save_market_calendar：取得データを DuckDB に冪等に保存（ON CONFLICT DO UPDATE）
    - fetched_at を UTC ISO8601 形式で記録して Look-ahead Bias を可視化
  - 型変換ヘルパー: _to_float / _to_int（不正値は None）

- DuckDB スキーマ (src/kabusys/data/schema.py)
  - DataLayer 構成に基づくスキーマを定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに妥当性制約（NOT NULL, CHECK, PRIMARY KEY, FOREIGN KEY 等）を設定
  - よく使われるクエリ向けのインデックスを定義（code/date や status 等）
  - init_schema(db_path) により DB ファイルの親ディレクトリ自動作成とテーブル作成を行う（冪等）
  - get_connection(db_path) により既存 DB へ接続可能（初回は init_schema を推奨）

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 日次 ETL のワークフローを実装:
    - run_daily_etl：カレンダー取得 → 株価 ETL → 財務 ETL → 品質チェック の順で実行
  - 差分更新戦略:
    - 最終取得日を基に差分取得を行い、バックフィル（デフォルト backfill_days=3）を実施して API の後出し修正を吸収
    - 市場カレンダーは先読み（lookahead_days=90）して営業日調整に利用
  - 個別ジョブ:
    - run_prices_etl, run_financials_etl, run_calendar_etl：それぞれ差分取得と保存を行い (fetched, saved) を返す
  - ETL の堅牢性:
    - 各ステップは独立して例外を捕捉し、1 ステップ失敗でも他ステップを継続（エラーは ETLResult.errors に蓄積）
  - ETL 結果を表す ETLResult データクラスを追加（取得数・保存数・品質問題・エラーを集約）
  - 市場カレンダーに基づく営業日調整関数 _adjust_to_trading_day を追加

- 品質チェックモジュール (src/kabusys/data/quality.py)
  - 品質チェックのためのフレームワークと主要チェックを実装:
    - QualityIssue データクラス（check_name, table, severity, detail, rows）
    - check_missing_data：raw_prices の OHLC 欠損検出（volume は対象外）。問題は severity="error" として報告
    - check_spike：前日比のスパイク検出（LAG を用いた SQL 実装、デフォルト閾値 50%）
  - 仕様としては重複チェック・将来日付/営業日外検出も想定（ドキュメント記載）
  - 各チェックは問題を全件収集して返す（Fail-Fast ではない）。DuckDB のパラメータバインドを使用

- 監査ログ (Audit) (src/kabusys/data/audit.py)
  - シグナルから約定までのトレーサビリティを確保する監査テーブルを実装:
    - signal_events（戦略が生成したシグナル・棄却ログ等）
    - order_requests（発注要求、order_request_id を冪等キーとして扱う）
    - executions（証券会社側の約定ログ、broker_execution_id をユニーク化）
  - ステータス・制約・チェックを厳密に定義（order_type に応じた price チェック等）
  - すべての TIMESTAMP を UTC で扱う（init_audit_schema で SET TimeZone='UTC' を実行）
  - init_audit_schema(conn) / init_audit_db(db_path) による初期化関数を提供
  - 監査向けの検索インデックスを多数追加（signal_events の日付/戦略索引、order_requests の status 索引等）

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 既知の注意点 (Notes)
- quality モジュールのドキュメントでは複数のチェック項目が列挙されていますが、現実装では主に欠損チェックとスパイク検出が実装されています（重複/日付不整合のチェックは将来的な拡張を想定）。
- J-Quants API のリクエストは urllib を使用しており、タイムアウトや HTTPError のハンドリングを行っています。環境やネットワーク条件によっては追加の耐障害処理（接続プールや非同期対応）が必要になる場合があります。
- DuckDB のデータ型・制約は設計時に厳密なチェックを導入しています。既存データの移行時は制約違反に注意してください。

---

今後の予定（例）
- strategy / execution / monitoring サブパッケージの実装拡充（実際の発注ロジック、リスク管理、監視通知等）
- quality モジュールのチェック拡張（重複検出、将来日付・営業日外検出）
- 非同期/並列で API 呼び出しと保存を高速化する仕組み
- テストカバレッジの充実と CI 統合

---