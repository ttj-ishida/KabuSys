# Changelog

すべての重要な変更点は Keep a Changelog の規約に従って記載しています。  
日付はコードベースの状態を確認した日付（2026-04-17）を使用しています。なお、多くの記述はソースコードの実装から推測してまとめたものであり、実際のリリースノートや設計文書と差異がある場合があります。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-17

### Added
- 基本パッケージ情報を追加
  - kabusys.__version__ = 0.1.0 を設定。

- 実行用エントリポイント
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整可能（デフォルト 60 秒）。
    - プロジェクトルート下 data/stop_requested.flag による停止フラグを検出して安全に終了。
    - 監視処理は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視用 DB を本番と共通で扱う設計）。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - 起動時に data/execution.pid を使った PID 管理、data/stop_requested.flag による停止制御に対応。

- 環境設定・ローダー
  - kabusys.config.Settings クラスを追加し、環境変数経由で設定を提供。
  - .env/.env.local 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - 読み込み順序: OS 環境 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサーは export KEY=val 形式、クォート、エスケープ、インラインコメントなどに対応。
  - 多数の設定プロパティを提供（例: DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH / CPU/MEM/DISK 閾値など）。
  - 設定値のバリデーションを追加（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。

- DB 初期化ユーティリティ
  - 監視テーブルを初期化する init_monitoring_db を利用して起動時にテーブル存在を保証（冪等）。

- Execution コンポーネント（起動スクリプトから組み立てる主要コンポーネント）
  - BrokerClientFactory によるブローカークライアント生成（ペーパートレード時はモックを使用）。
  - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine といった実行系コンポーネントの組立てと起動処理。
  - RiskManager デフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を実装。初期ポートフォリオ値は broker.get_available_cash() から取得。

- ユーティリティ
  - utils.process_priority: クロスプラットフォームのプロセス優先度設定ユーティリティを追加（set_process_priority）。
    - Windows・POSIX（Linux, Darwin, FreeBSD）を扱い、未対応 OS や権限不足時は警告を出してスキップ。
  - CPU 固定ユーティリティ（set_cpu_affinity）を追加。

- Portfolio（銘柄選定・配分・サイズ計算）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順で候補選定。signal_rank によるタイブレーク。
    - calc_equal_weights, calc_score_weights: 配分重み計算（スコア全ゼロ時は等金額にフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限ロジック（既存ポジションを考慮して候補をフィルタ）。
    - calc_regime_multiplier: 市場レジームに応じた資金乗数を返す（bull/neutral/bear）。
  - portfolio.position_sizing:
    - calc_position_sizes: 等配分 / スコア加重 / リスクベース（risk_based）に対応した発注株数計算と aggregate cap スケーリング、単元株丸め、cost_buffer を考慮した保守的見積り。

- Research（DuckDB を利用したファクター計算・解析）
  - research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率の計算。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率等の計算。
    - calc_value: PER / ROE を raw_financials と prices_daily から計算。
  - research.feature_exploration:
    - calc_forward_returns: 将来リターン計算（horizons 指定可、入力検証あり）。
    - calc_ic: スピアマンランク相関（IC）計算（欠測/少数データ考慮）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を算出。
    - rank: ランク変換（同順位は平均ランク）。
  - research.__init__ に zscore_normalize を再エクスポート（kabusys.data.stats 依存）。

- Tools
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを算出し PASS/FAIL 判定を行う CLI。
    - 引数で期間（--from, --to）と DB パス（--db）を指定可能。
    - デフォルト DB は data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）。
    - 各種閾値を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）。

- AI ニュース NLP（途中実装）
  - ai.news_nlp:
    - raw_news から銘柄ごとのニュースを集約し OpenAI API（gpt-4o-mini）でセンチメントスコア（-1.0〜1.0）を生成して ai_scores テーブルに書き込む設計。
    - バッチ処理、トークン肥大対策（記事数・文字数制限）、リトライ（429/5xx/タイムアウト等）等の設計が含まれる。
    - calc_news_window, score_news などの関数を用意（score_news は API キー検査とウィンドウ計算まで実装）。
    - 出力 JSON の厳密検証、スコアクリッピング、部分更新（DELETE/INSERT）による部分失敗耐性を意図。

### Changed
- 設計上の分離
  - paper_trading 環境では SQLite を分離（PAPER_TRADING_SQLITE_PATH / settings.paper_sqlite_path）して本番 DB のデータと完全に分離することを明確化。
- 環境ロードの既定動作
  - OS 環境変数を保護し、.env.local が .env を上書きする優先度で読み込まれる挙動を明示。

### Fixed
- 各種入力検証の追加
  - MONITOR_POLL_INTERVAL の不正値に対するフォールバック（ログ出力してデフォルト値を使用）。
  - PAPER_FILL_MODE の許容値チェック（不正時は ValueError）。
  - Settings.env / log_level のバリデーション。
  - calc_forward_returns の horizons バリデーション（正の整数かつ 252 以下）。

### Deprecated
- （なし）

### Removed
- （なし）

### Security
- OpenAI API キーは明示的に引数または環境変数 OPENAI_API_KEY で解決され、未設定時は例外を発する（キーの未設定で誤動作しない設計）。

---

注記・補足
- 多くの関数・モジュールは DuckDB / SQLite のテーブル構造（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, system_status, trade_logs, risk_logs など）を前提としています。これらのテーブル定義は本 changelog には含まれていませんが、実行には事前定義が必要です。
- ai.news_nlp モジュールはファイル末尾で処理中に途切れている部分があり、実装は未完了の可能性があります（ソース末尾の切れが確認されます）。実運用前に完全な例外処理・トランザクション処理・API 応答バリデーションの追加を推奨します。
- run_monitoring/run_execution ではプロセス優先度設定（set_process_priority）を起動時に実行するため、権限不足や未対応 OS 上では警告が出る点に注意してください。

もし特定モジュール（例: ai.news_nlp の未完部分、DB スキーマ、API クライアントの詳細など）に基づいたより詳しいリリースノートやマイグレーション手順が必要であれば、該当ファイルの追加情報を与えてください。