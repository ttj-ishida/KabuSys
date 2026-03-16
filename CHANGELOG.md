# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

※ 初期リリース（v0.1.0）について、ソースコードから推測できる機能・設計方針・環境設定を記載しています。

## [0.1.0] - 2026-03-16
### Added
- パッケージ初期リリース: kabusys
  - パッケージルートおよびバージョン: src/kabusys/__init__.py にて __version__ = "0.1.0" を定義。

- 環境設定モジュール（kabusys.config）
  - .env ファイルと環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルート判定は .git または pyproject.toml を起点に探索（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - .env パースの細かい挙動:
      - export KEY=val 形式に対応。
      - シングル／ダブルクォート内のバックスラッシュエスケープ処理をサポート。
      - クォートなしの場合はインラインコメント（#）を条件付きで無視。
    - .env の読み込みで OS 環境変数を保護する protected 処理を実装（上書き防止）。
  - Settings クラスを提供（settings オブジェクトとして公開）。
    - J-Quants / kabuステーション / Slack / DB パス / システム設定（KABUSYS_ENV, LOG_LEVEL）などのプロパティを定義。
    - env / log_level の値検証（許容値チェック）、便宜的な is_live / is_paper / is_dev プロパティ。
  - 必須環境変数が未設定の場合に ValueError を投げる _require 関数。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出し（HTTP）ラッパーを実装。
    - ベース URL: https://api.jquants.com/v1（定数化）。
    - レート制限（120 req/min）を守る固定間隔スロットリング（_RateLimiter）。
    - 冪等・効率的なページネーション処理（pagination_key の扱い）。
    - リトライ戦略:
      - 最大再試行回数 3 回、指数バックオフ（base=2.0 秒）。
      - ステータス 408/429 および 5xx を対象にリトライ。
      - 429 時は Retry-After ヘッダを優先して待機時間を決定。
      - ネットワークエラー（URLError/OSError）に対する再試行。
    - 401 Unauthorized 受信時はリフレッシュトークンで id_token を自動更新して 1 回だけ再試行（無限再帰防止のため allow_refresh フラグ）。
    - id_token のモジュールレベルキャッシュを実装（ページネーション間で共有）。
  - データ取得関数:
    - fetch_daily_quotes: 株価日足（OHLCV）の取得（ページネーション対応）。
    - fetch_financial_statements: 四半期財務データの取得（ページネーション対応）。
    - fetch_market_calendar: JPX マーケットカレンダーの取得。
    - 取得時刻（fetched_at）など Look-ahead Bias 対策を考慮した設計をコメントで明記。
  - DuckDB への保存関数（冪等化）:
    - save_daily_quotes / save_financial_statements / save_market_calendar は INSERT ... ON CONFLICT DO UPDATE を利用して重複を排除し、冪等に保存。
    - PK 欠損行はスキップし、スキップ件数をログに出力。
  - 型変換ユーティリティ: _to_float, _to_int（妥当性チェックや float 経由の変換ルールを実装）。

- DuckDB スキーマ定義と初期化（kabusys.data.schema）
  - DataPlatform に基づく 3 層 + execution 層のテーブル定義を実装:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - テーブル作成用 DDL とインデックス定義（よく使うクエリパターンに合わせたインデックス）を含む。
  - init_schema(db_path) によりディレクトリ自動作成→接続→DDL 実行（冪等）を行う API を提供。
  - get_connection(db_path) で既存 DB へ接続（スキーマ初期化は行わない）。

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL の統合エントリ run_daily_etl を実装（市場カレンダー→株価→財務→品質チェックの順で処理）。
  - 個別ジョブの実装:
    - run_calendar_etl: カレンダーの差分 ETL（デフォルト先読み 90 日）。
    - run_prices_etl: 株価の差分 ETL（差分判定・デフォルトバックフィル 3 日）。
    - run_financials_etl: 財務の差分 ETL（差分判定・バックフィル対応）。
  - 差分更新ヘルパー:
    - 最終取得日の自動取得（raw_* の MAX 日付）と backfill の計算（初回は _MIN_DATA_DATE を起点）。
  - 営業日調整ヘルパー (_adjust_to_trading_day): カレンダーに基づいて target_date を直近営業日に補正（最大 30 日まで遡る）。
  - ETLResult dataclass を提供:
    - ETL 実行結果の構造化（取得数、保存数、品質問題リスト、エラーメッセージなど）。
    - has_errors / has_quality_errors / to_dict などのユーティリティ。
  - 品質チェックモジュール（quality）との連携（run_quality_checks 引数で制御）。

- 監査ログ（トレーサビリティ）用スキーマ（kabusys.data.audit）
  - 監査ログテーブルを別モジュールで定義・初期化する API を追加:
    - signal_events: 戦略が生成したシグナルの記録（decision, reason, created_at など）。
    - order_requests: 発注要求ログ（order_request_id を冪等キーとして定義）。limit/stop/market のチェックを DDL に含む。
    - executions: 証券会社の約定ログ（broker_execution_id をユニーク冪等キーに想定）。
  - 監査用インデックス群を定義（検索パターンに応じたインデックス）。
  - init_audit_schema(conn) と init_audit_db(db_path) を提供。UTC タイムゾーンの設定を行う（SET TimeZone='UTC'）。

- データ品質チェックモジュール（kabusys.data.quality）
  - QualityIssue dataclass を定義（check_name, table, severity, detail, rows）。
  - 実装済みのチェック:
    - check_missing_data: raw_prices の OHLC 欠損検出（volume は許容）。
    - check_spike: 前日比スパイク検出（LAG ウィンドウ関数を使い、デフォルト閾値 50%）。
  - チェックは全件収集方式（Fail-Fast ではなく問題をリストで返す）。DuckDB 上で SQL により効率的に実行。

### Changed
- 初回リリースのため変更履歴なし。

### Fixed
- 初回リリースのため修正履歴なし。

### Notes / 環境変数
- 必須または使用される環境変数（settings による想定）:
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (任意, デフォルト http://localhost:18080/kabusapi)
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
  - DUCKDB_PATH (任意, デフォルト data/kabusys.duckdb)
  - SQLITE_PATH (任意, デフォルト data/monitoring.db)
  - KABUSYS_ENV (任意, 値: development|paper_trading|live。デフォルト development)
  - LOG_LEVEL (任意, DEBUG|INFO|WARNING|ERROR|CRITICAL。デフォルト INFO)
  - KABUSYS_DISABLE_AUTO_ENV_LOAD (任意, 1 を設定すると .env の自動読み込みを無効化)

### Implementation / Design Remarks
- J-Quants クライアントはレートリミット・リトライ・トークン自動更新・ページネーション・取得時刻（fetched_at）記録など、実運用を想定した堅牢な実装方針が採られています。
- DuckDB スキーマは Raw → Processed → Feature → Execution の分離により再現性とデバッグ性を確保。多くのテーブルに PRIMARY KEY / CHECK 制約を付与、インデックス設計も含む。
- ETL は差分取得・バックフィル・品質チェックを組み合わせ、1 ステップ失敗時も他ステップは継続する寛容な設計（呼び出し側が結果に応じて処理を判断）。
- 監査ログはトレーサビリティ重視で UUID を階層的に連鎖させる想定。order_request_id を冪等キーとして二重発注防止を意図。
- すべてのタイムスタンプは UTC を前提（監査モジュールは明示的に SET TimeZone='UTC' を実行）。

---

今後のリリースで期待される項目（例）:
- execution 層の実際のブローカー連携（kabu API）実装
- strategy / monitoring の具象実装・テスト
- quality チェックの追加（重複、日付不整合などの完全実装）
- CI / テスト・ドキュメントの整備

（以上）