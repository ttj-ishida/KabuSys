# Changelog

すべての変更は Keep a Changelog の形式に従い、日本語で記載しています。

## [Unreleased]

## [0.1.0] - 初回リリース (推定)

リリース日: 未設定

### Added
- 全体
  - 初期リリース相当の主要モジュール群を追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 実行用スクリプト
  - run_monitoring.py
    - SystemMonitor を定期ポーリングで実行する起動スクリプトを追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）で上書き可能。無効な値はデフォルトにフォールバック。
    - 監視は常に本番用の sqlite_path を使用（環境に依らず監視 DB を共通利用する設計）。
    - 停止制御にプロジェクト直下の `data/stop_requested.flag` を使用し、検知時にループを終了。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は Paper Trading 用の専用 SQLite（`data/paper_trading.db` または環境変数で上書き）を使用し、本番 DB と完全分離。
    - BrokerClientFactory を用いて実行時に実ブローカー／モックを切り替え。
    - エンジンは別スレッドで実行され、`data/stop_requested.flag` により安全停止する仕組み。
    - 実行 PID ファイル（`data/execution.pid` など）を扱う設定を持つ。

- 設定管理 / 初期化 / 検証
  - config.py
    - 環境変数読み込み・ラッパー `Settings` を実装。
    - .env 自動読み込み機能を実装（プロジェクトルート検出: `.git` または `pyproject.toml` を探索）。
    - 読み込み優先順: OS 環境変数 > .env.local > .env。自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env パーサは `export KEY=val` 形式、引用文字列（シングル/ダブルクォート、バックスラッシュエスケープ）やインラインコメントの取り扱いに対応。
    - 必須項目取得ヘルパ `_require()` による未設定時の明示的エラーを提供。
    - J-Quants / kabuステーション / DB パス / 監視閾値等のプロパティを実装（例: `duckdb_path`, `sqlite_path`, `paper_sqlite_path`, `pid_file_path`, `cpu_threshold_pct` 等）。
    - `PAPER_FILL_MODE` の値検証（許容値: "instant" | "partial" | "never" | "reject"）。不正値は例外を投げる。
    - `KABUSYS_ENV` の検証（"development", "paper_trading", "live" のみ）と簡易フラグ `is_live`, `is_paper`, `is_dev` を提供。
  - config_setup.py
    - 対話式ウィザードで .env を初期生成／更新する CLI を追加。
    - シークレット入力、デフォルト値表示、選択肢チェック、既存 .env の読み込み・再利用をサポート。
    - 最終確認後に .env を安全なテンプレート形式で書き出す。
  - validate_config.py
    - 起動前に環境変数や config/*.yaml の有無・簡易妥当性を検査する CLI を追加。
    - 必須環境変数チェック、`KABUSYS_ENV` / `LOG_LEVEL` の妥当性チェック、DB パスの親ディレクトリ存在チェック、PyYAML があれば YAML のパース検証を行う。
    - `--strict` オプションで警告も失敗扱いにできる。
    - 本番環境向けのガード（LINE 通知設定未設定や Kill Switch の挙動警告）を実装。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 起動スクリプト共通のロギング設定関数 `setup_logging()` を追加。
    - StreamHandler を stdout に出力（stderr ではない点に注意）し、日次ローテーション（TimedRotatingFileHandler）でログファイルを出力。デフォルトログディレクトリは `logs/`、バックアップは 30 日分。
    - 既存ハンドラは再設定時にクリアする（重複防止）。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続するフェイルセーフあり。
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度を設定する `set_process_priority()` を追加。psutil を利用し、権限不足や未対応 OS の場合は安全に警告してスキップ。
    - `set_cpu_affinity()` を提供し、最初の N コアにプロセスをピンニングできる。引数検証・例外ハンドリングあり。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル候補選択 `select_candidates()`（スコア降順、同点時は signal_rank でタイブレーク）。
    - 等分配 `calc_equal_weights()`、スコア加重 `calc_score_weights()` を実装。全スコアが 0 の場合は等分配にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - `apply_sector_cap()`：既存保有のセクター比率が上限を超える場合に当該セクターの新規候補を除外。unknown セクターは上限適用対象外。
    - `calc_regime_multiplier()`：市場レジーム（"bull"/"neutral"/"bear"）に応じた資金乗数を返す。未知のレジームは 1.0 にフォールバックして警告。
  - portfolio/position_sizing.py
    - ポジションサイズ決定ロジック `calc_position_sizes()` を実装。
    - allocation_method として `"risk_based"`, `"equal"`, `"score"` をサポート。
    - lot_size（単元）で丸め、1銘柄上限（max_position_pct）や利用可能現金（available_cash）を考慮した aggregate cap スケーリングを実装。
    - cost_buffer により手数料・スリッページを保守的に見積もる機能、スケーリング時の端数配分ロジックを実装。
    - price 欠損時のスキップやログ出力にも対応。

- リサーチ（ファクター計算）
  - research/factor_research.py（未完の箇所あり）
    - Momentum / Value / Volatility / Liquidity 等の定量ファクター計算方針を実装するためのモジュール骨格を追加。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計。
    - モメンタム計算の定数（例: 1M/3M/6M、MA200、ATR など）を定義。
    - （ファイル末尾が切れているため一部実装が続く想定）

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード履歴（SQLite）から検証レポートを生成する CLI を追加。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率、API レイテンシ（avg/max/P95）などを集計し、閾値に基づく PASS/FAIL 判定を行う。
    - デフォルト閾値（稼働率 >= 99%、fill >= 90% 等）を定義。
    - 日付フィルタ（--from / --to）および DB パス指定（--db / 環境変数）をサポート。

- 監視 DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を run_* スクリプトから呼び出して、監視用テーブルの存在を保証（冪等）。

### Changed
- ロギング
  - コンソール出力は stdout に明示的に出すよう統一（cron/Task Scheduler でのリダイレクトを想定）。
- デフォルト挙動
  - run_monitoring は監視用途のため、KABUSYS_ENV にかかわらず「本番用の」sqlite_path を参照する設計になっている点を強調（意図的な隔離方針）。

### Fixed
- （初回リリース相当のため特定のバグフィックス履歴はなし）

### Notes / Usage
- CLI の例:
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - 監視起動: python -m kabusys.run_monitoring
  - Execution 起動: python -m kabusys.run_execution
  - ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD --to YYYY-MM-DD --db PATH]
- 環境変数の主なキー:
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABUSYS_ENV（development | paper_trading | live）
  - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
  - LOG_LEVEL, LOG_DIR
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔）
  - PAPER_FILL_MODE（paper_trading 時の挙動）
  - KILL_FLAG_CLEAR_ON_START（本番での危険性注意）

### Breaking Changes
- なし（初期リリース）

---

今後の改善・TODO（コード中コメントより推測）
- price 欠損時のフォールバック（前日終値や取得原価など）を position_sizing / apply_sector_cap に導入することで、欠損データによる過少評価を軽減する。
- 銘柄別単元（lot_size）を stocks マスタに持たせるなどの柔軟化。
- research/factor_research の未完パート実装とユニットテスト追加。
- ロギング関連でさらに細かいファイル分割や環境別設定（例: cloud storage へのログ転送）を検討。

以上。必要であれば、セクション分けや日付の追加、個別ファイルごとの詳細な変更点（関数一覧や引数仕様）をさらに展開します。