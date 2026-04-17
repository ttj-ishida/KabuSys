# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) 準拠で記載しています。

## [Unreleased]

## [0.1.0] - 2026-04-17
初回リリース

### Added
- 基本パッケージ情報
  - パッケージメタ情報を追加（kabusys.__version__ = 0.1.0）。

- 実行スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告してデフォルトにフォールバック。
    - 監視プロセス起動時にプロセス優先度を "high" に設定。
    - 監視用 DB は環境に依らず本番用 sqlite_path を使用。
    - 停止フラグファイル（data/stop_requested.flag）でループを終了可能。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を利用し、paper_trading 用の専用 SQLite（data/paper_trading.db）に記録して本番 DB と完全分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグファイルの検知でエンジン停止処理を行う。
    - 実行用 PID ファイル管理（data/execution.pid）。

- 設定・環境読み込み
  - config.Settings
    - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - `.env` / `.env.local` の優先順位・上書きルールを実装（OS 環境変数は保護）。
    - `.env` パーサは `export KEY=val`、クォート文字、インラインコメント（スペース/タブ前の `#`）に対応。
    - 多数の設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境判定等）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化可能。
    - `PAPER_FILL_MODE` の妥当性チェック（instant/partial/never/reject）。
    - デフォルトの DB パス: `DUCKDB_PATH=data/kabusys.duckdb`, `SQLITE_PATH=data/monitoring.db`、paper_trading 用デフォルト `data/paper_trading.db`。

- モニタリング DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を利用して起動時に監視テーブルの存在を保証（冪等）。

- Execution コンポーネント
  - ExecutionEngine および関係コンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler 等）の起動フローを組み立てるスクリプトを追加。
  - RiskManager にデフォルト設定値を定義（position %, utilization, rate limit, circuit breaker, drawdown 等）。初期ポートフォリオ値は broker.get_available_cash() から取得。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - シグナル選別（select_candidates: スコア降順、同点は signal_rank でタイブレーク）。
    - 等金額・スコア加重の重み計算（calc_equal_weights, calc_score_weights）。スコア合計が 0 の場合は等金額にフォールバックし警告をログ出力。
  - portfolio.risk_adjustment
    - セクター集中の上限チェック（apply_sector_cap: 現有ポジションを考慮して同一セクターの新規候補を除外）。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier: bull/neutral/bear のマッピング、未知レジームはフォールバックして警告）。
  - portfolio.position_sizing
    - 各銘柄の発注株数決定ロジック（risk_based / equal / score の allocation_method をサポート）。
    - 単元（lot_size）丸め、1銘柄上限（max_position_pct）、総投下上限（available_cash に基づく aggregate cap）、コストバッファ（cost_buffer）を考慮したスケールダウン処理。
    - スケールダウン時の端数配分ロジック（fractional remainder に基づき lot 単位で追加配分）。

- ユーティリティ
  - utils.process_priority
    - プラットフォーム非依存でプロセス優先度設定（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値を設定）。
    - CPU affinity 設定ユーティリティ（set_cpu_affinity）を追加。実行権限がない場合は警告してスキップ。

- リサーチ / ファクター計算
  - research.factor_research
    - モメンタム、ボラティリティ、バリュー系ファクター計算関数を追加（calc_momentum, calc_volatility, calc_value）。
    - DuckDB を用いた SQL 集約で計算。窓長や必要なデータ行数が満たされない場合は None を返す安全設計。
  - research.feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（Spearman ランク相関）計算（calc_ic）、ファクター統計サマリ（factor_summary）、ランク変換ユーティリティ（rank）を追加。
    - 外部依存なし（標準ライブラリのみ）で実装。
  - research パッケージは zscore_normalize（kabusys.data.stats 経由）を含むエクスポートを用意。

- ツール
  - tools.paper_verification_report
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 指標: 稼働率 (uptime)、注文成功率（fill rate）、送信率（send rate）、レイテンシ（avg / max / P95）、リスク却下数。
    - デフォルト閾値を定義（稼働率 >=99.0%、fill >=90%、send >=95%、P95 <=200ms）。
    - 日付フィルタ (--from / --to)、DB パス指定 (--db または env PAPER_TRADING_SQLITE_PATH) に対応。
    - DB テーブル存在チェックにより SQL エラーを捕捉して N/A を出力するフォールトトレラントな実装。

- AI / ニュース NLP（初期実装）
  - ai.news_nlp
    - raw_news / news_symbols を集約して OpenAI API（gpt-4o-mini）へバッチ送信し、銘柄別のセンチメントスコアを ai_scores に書き込むロジックを追加（スコアは ±1.0 にクリップ）。
    - バッチサイズ、最大記事数/文字数によるトークン制御、最大リトライ回数（429/5xx/接続エラーに対する指数バックオフ）などの設計方針を採用。
    - ニュース収集ウィンドウ計算ユーティリティ（calc_news_window）を追加（JST ベースの時間ウィンドウを UTC に変換）。
    - API キーは引数または環境変数 `OPENAI_API_KEY` から解決、未設定時は ValueError を送出。
    - 実装はフェイルセーフを重視し、部分失敗時に他コードの既存スコアを保護する上書き戦略を採用（DELETE / INSERT による置換、コード絞り込み）。

### Changed
- ドキュメント・設計コメントをコード内に充実させ、設計方針（ルックアヘッドバイアス回避、外部 API への非依存、純粋関数重視等）を明示。

### Fixed
- run_monitoring と run_execution の起動フローにおいて、DB 初期化（監視テーブル）や停止フラグの早期チェックを追加し、安全に起動/停止できるように改善。

### Notes / Known limitations
- .env 自動読み込みはプロジェクトルートが検出できない場合はスキップされる。
- 一部の処理は実行権限（プロセス優先度変更、CPU affinity 設定）や OS に依存し、権限不足や未対応 OS の場合は警告を出してスキップする設計です。
- ai.news_nlp の実行は OpenAI API 利用（課金）および API レート制限に注意してください。API 呼び出し失敗はバックオフでリトライしますが、最終的に失敗した場合は該当銘柄のスコア更新をスキップします。
- DuckDB の executemany に関する注意（コメント内記載）など、外部ライブラリの制約に対するガードを実装しています。

---

今後の予定（アイデア）
- ExecutionEngine / Broker 実装の拡充とエンドツーエンドの統合テスト。
- 銘柄別単元（lot size）や手数料スリッページモデルの拡張。
- ai.news_nlp のエラーハンドリング強化およびスケジューリング機構の追加。