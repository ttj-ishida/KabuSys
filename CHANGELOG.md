Keep a Changelog
=================

すべての重要な変更履歴はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。

0.1.0 - 2026-03-16
-----------------

Added
- 初回リリース。日本株自動売買システムのコアコンポーネントを実装。
  - パッケージエントリポイント
    - kabusys.__init__ にバージョン `0.1.0` と公開モジュール一覧を追加。
  - 設定／環境変数管理 (kabusys.config)
    - .env ファイルと OS 環境変数から設定を自動読み込み（プロジェクトルート判定: .git または pyproject.toml）。
    - 自動読み込みを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - .env の柔軟なパーサ実装: `export KEY=val` 形式対応、シングル/ダブルクォートのエスケープ処理、インラインコメントの扱いを改善。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 実行環境 / ログレベルなどのプロパティ経由でアクセス可能。
    - 必須環境変数未設定時には明確な ValueError を発生させる `_require` を実装。
    - デフォルトやバリデーション:
      - KABUSYS_ENV: development / paper_trading / live のいずれか（不正値は例外）。
      - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL のみ。
      - KABU_API_BASE_URL のデフォルトは http://localhost:18080/kabusapi
      - DB のデフォルトパス: DUCKDB_PATH = data/kabusys.duckdb, SQLITE_PATH = data/monitoring.db
  - データ取得クライアント (kabusys.data.jquants_client)
    - J-Quants API クライアントを実装。
    - レート制御: 120 req/min に準拠する固定間隔スロットリング (RateLimiter)。
    - リトライロジック: 指数バックオフ、最大 3 回、HTTP 408/429 と 5xx を再試行対象に設定。
    - 401 受信時は ID トークンを自動リフレッシュして 1 回リトライ（無限再帰を回避するフラグ）。
    - ページネーション対応の取得関数を提供:
      - fetch_daily_quotes (株価日足: OHLCV)
      - fetch_financial_statements (四半期財務)
      - fetch_market_calendar (JPX カレンダー)
    - モジュールレベルの ID トークンキャッシュを導入し、ページネーション間でトークンを共有。
    - DuckDB への保存関数（冪等性あり）:
      - save_daily_quotes, save_financial_statements, save_market_calendar
      - ON CONFLICT DO UPDATE により重複を排除し上書きする設計。
      - 保存時に fetched_at（UTC ISO8601）を付与、PK 欠損行はスキップして警告ログ出力。
    - 型変換ユーティリティ: _to_float / _to_int（不正値や空文字に対する堅牢処理、"1.0" のような浮動小数点文字列の int 変換判断など）。
  - DuckDB スキーマ定義と初期化 (kabusys.data.schema)
    - DataPlatform の 3 層アーキテクチャに基づくスキーマ実装:
      - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
      - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - Feature Layer: features, ai_scores
      - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 監査・実行処理向けに各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）を定義。
    - 頻出クエリを想定したインデックス群を作成。
    - init_schema(db_path) でディレクトリ作成を含めた初期化を実施（:memory: サポート）。get_connection() も提供。
  - ETL パイプライン (kabusys.data.pipeline)
    - 日次 ETL の総合エントリ: run_daily_etl を実装。処理順は:
      1. 市場カレンダー ETL（先読み default 90 日）
      2. 株価日足 ETL（差分取得・バックフィル default 3 日）
      3. 財務データ ETL（差分取得・バックフィル default 3 日）
      4. 品質チェック（オプション）
    - 差分更新ロジック: DB の最終取得日から未取得期間のみ取得。初回は J-Quants の最小データ開始日 (2017-01-01) から取得。
    - backfill_days により最終取得日の過去数日を再取得して API の後出し修正を吸収。
    - ETLResult dataclass を導入し、各ステップの取得件数・保存件数・品質問題・エラーの集約を行う。
    - 各ステップは独立したエラーハンドリング（1 ステップ失敗でも他は継続）を行い、エラーは集約して返す設計。
    - 市場カレンダー取得後に target_date を営業日に調整するユーティリティを提供（_adjust_to_trading_day）。
  - データ品質チェック (kabusys.data.quality)
    - QualityIssue dataclass を導入（check_name, table, severity, detail, rows）。
    - 実装済みのチェック:
      - check_missing_data: raw_prices の OHLC 欄の欠損検出（欠損があれば severity="error"）。
      - check_spike: 前日比の急騰・急落（デフォルト閾値 50%）を検出。
    - 各チェックはサンプル行を返し、Fail-Fast せずすべての問題を収集する方針。
  - 監査ログ（トレーサビリティ）機能 (kabusys.data.audit)
    - シグナル→発注→約定のトレーサビリティ用テーブルを定義:
      - signal_events, order_requests, executions
    - order_request_id を冪等キーとして扱い二重発注を防止。
    - すべての TIMESTAMP は UTC で保存する（init_audit_schema は SET TimeZone='UTC' を実行）。
    - 監査用途のインデックス群を作成。
    - init_audit_schema(conn) / init_audit_db(db_path) を提供。

Changed
- （初回リリースのため過去変更なし）

Fixed
- （初回リリースのため過去修正なし）

Security
- （公開時点での既知のセキュリティ修正は無し）

Notes / 運用メモ
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  未設定時は Settings の該当プロパティアクセスで ValueError が発生します。
- 自動 .env ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（主にテスト時に利用）。
- DuckDB 初期化:
  - schema.init_schema(db_path) を初回実行してスキーマを作成してください（db_path の親ディレクトリは自動作成されます）。
- ETL の使い方例:
  - run_daily_etl(conn) を呼ぶことでカレンダー → 株価 → 財務 → 品質チェックまでを実行し、ETLResult を受け取れます。
- J-Quants API の利用時はレート制限を厳守する設計になっています。ローカルネットワークの反応や証明書問題など、ネットワーク例外はリトライ対象となります。

Acknowledgements / TODO
- 将来的な拡張候補:
  - execution / strategy / monitoring パッケージの詳細実装（現状はパッケージディレクトリのみを用意）。
  - 追加の品質チェック（重複・日付不整合チェックなど）を拡充。
  - テストカバレッジの強化、モック API による統合テストの追加。

---