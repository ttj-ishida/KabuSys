# Changelog

すべての注目すべき変更を記録します。フォーマットは "Keep a Changelog" に準拠します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-18

### Added
- 全体
  - 初回リリース。本プロジェクトは日本株自動売買システム「KabuSys」として以下の主要コンポーネントを実装。
  - パッケージバージョンは `kabusys.__version__ = "0.1.0"`。

- 設定管理
  - 環境変数/`.env` 読み込みと管理を行う `src/kabusys/config.py` を追加。
    - プロジェクトルートを `.git` または `pyproject.toml` から自動検出して `.env` / `.env.local` をロード（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロード無効化可能）。
    - `.env` パーシングは `'`/`"` のクォートやエスケープ、`export KEY=val`、行内コメントを考慮して安全に処理。
    - 各種設定キーを `Settings` クラスのプロパティとして提供（例: `duckdb_path`, `sqlite_path`, `paper_sqlite_path`, `pid_file_path`, `cpu_threshold_pct` など）。
    - 入力検証を行うプロパティ（`env`, `log_level`, `paper_fill_mode` 等）があり、不正値は例外を送出。

- 設定ウィザード / 検証
  - 対話式 `.env` 生成/更新ウィザード `src/kabusys/config_setup.py` を追加。
    - 実行例: `python -m kabusys.config_setup`
    - シークレット入力のマスク、デフォルト値表示、保存確認機能を備える。
  - 起動前設定検証 CLI `src/kabusys/validate_config.py` を追加。
    - 必須環境変数チェック、`KABUSYS_ENV`/`LOG_LEVEL` 検証、DBパスの親ディレクトリ確認、`config/*.yaml` の存在/パース検証（PyYAML が無い場合はパース検証をスキップして警告）。
    - `--strict` オプションで警告を FAIL 扱いにできる。
    - 実行例: `python -m kabusys.validate_config`、`python -m kabusys.validate_config --strict`

- 実行/監視起動スクリプト
  - Execution エンジン起動スクリプト `src/kabusys/run_execution.py` を追加。
    - プロセス優先度を `high` に設定（`set_process_priority("high")`）。
    - `Settings` を経由して DB 接続を行う。`KABUSYS_ENV=paper_trading` の場合は `paper_sqlite_path`（デフォルト `data/paper_trading.db`）を使用し、本番 DB と分離。
    - ブローカークライアントは `BrokerClientFactory.create(settings)` で生成（paper_trading 時は MockBrokerClient を使用する想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、`ExecutionEngine` をデーモンスレッドで起動。停止フラグ（`data/stop_requested.flag`）を検知して安全停止。
    - PID ファイル管理をサポート（`data/execution.pid` デフォルト）。
    - `RiskConfig` のデフォルト値を設定（例: `max_position_pct=0.20`, `max_utilization=0.80`, `rate_limit_per_sec=5`, `circuit_breaker_errors=10`, `circuit_breaker_window_sec=60`, `max_drawdown=0.20` 等）。初期の `initial_portfolio_value` は broker から取得。

  - Monitoring ポーリングループ起動スクリプト `src/kabusys/run_monitoring.py` を追加。
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 停止フラグ `data/stop_requested.flag` の検知でループ終了。
    - Monitoring は環境にかかわらず本番用の `sqlite_path`（`data/monitoring.db` デフォルト）を使用する仕様。
    - SQLite / DuckDB の接続初期化（監視用テーブルの初期化を保証する `init_monitoring_db` 呼び出し）。

- ロギング / プロセス制御ユーティリティ
  - `src/kabusys/utils/logging_setup.py`
    - ルートロガーに対してコンソール（stdout）出力と日次ローテートのファイルハンドラ（TimedRotatingFileHandler）を設定。
    - ログレベルとログディレクトリは引数または環境変数（`LOG_LEVEL`, `LOG_DIR`）で解決。ファイルハンドラ作成失敗時はコンソールのみで継続。
    - ログファイル名は `<log_dir>/<app_name>.log`（例: `logs/execution.log`）。

  - `src/kabusys/utils/process_priority.py`
    - `psutil` を用いて Windows / POSIX に対応したプロセス優先度設定機構を提供（`set_process_priority("high"|"normal"|"low")`）。
    - CPU affinity を最初の N コアに固定する `set_cpu_affinity` も提供。権限不足等は警告ログでスキップ。

- ポートフォリオ構築（純粋関数群）
  - `src/kabusys/portfolio/portfolio_builder.py`
    - シグナルの候補選定 `select_candidates`（スコア降順、タイブレークは `signal_rank`）。
    - 等配分 `calc_equal_weights`、スコア加重 `calc_score_weights`（全スコアが 0 の場合は等配分へフォールバック）。
  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中制限 `apply_sector_cap`（既存保有のセクター比率が閾値を超える場合、新規候補を除外）。"unknown" セクターは制限の対象外。
    - レジームに応じた投下資金乗数 `calc_regime_multiplier`（"bull":1.0, "neutral":0.7, "bear":0.3。未知レジームは警告して 1.0 にフォールバック）。
  - `src/kabusys/portfolio/position_sizing.py`
    - 各銘柄の発注株数を決定する `calc_position_sizes` を実装。
      - allocation_method: `"risk_based"`（リスクベース）および `"equal"` / `"score"` に対応。
      - 単元株（lot_size, デフォルト 100）丸め、1銘柄上限 (`max_position_pct`)、全体利用率上限 (`max_utilization`)、コストバッファを考慮した aggregate cap のスケールダウンロジックを持つ。
      - リスクベースでは `risk_pct`、`stop_loss_pct` を使用してベース株数を計算。

- 解析 / リサーチ
  - `src/kabusys/research/factor_research.py`（ファクター計算モジュール）を追加（部分実装）。
    - Momentum / Value / Volatility / Liquidity 等の定量ファクターを DuckDB の `prices_daily` / `raw_financials` を参照して計算する設計。
    - モーメンタム計算（`calc_momentum`）の骨格と定数（例: 1M/3M/6M、MA200、ATR20 等）を実装。

- ツール
  - Paper Trading 向け検証レポート生成スクリプト `src/kabusys/tools/paper_verification_report.py` を追加。
    - `PAPER_TRADING_SQLITE_PATH` 環境変数（デフォルト `data/paper_trading.db`）を参照してレポートを生成。
    - 指標: 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下件数、レイテンシ（平均/最大/P95）を報告。
    - デフォルトの合格基準（閾値）を定義: 稼働率 >= 99.0%、注文成功率 >= 90.0%、送信率 >= 95.0%、P95 レイテンシ <= 200 ms。
    - 日付範囲フィルタ `--from` / `--to`、DB パス上書き `--db` をサポート。
    - P95 計算、NULL / データ欠損時の安全な扱い（N/A 表示）を実装。

- パッケージ構成
  - `src/kabusys/portfolio/__init__.py`、`src/kabusys/tools/__init__.py` を追加して各モジュールを公開。

### Changed
- （初回リリースのためなし）

### Fixed
- （初回リリースのためなし）

---

注: 上記はソースコードから推測してまとめた初期リリースの変更点一覧です。実際のリリースノートとして利用する場合は、ビルド手順、既知の制約や互換性情報、テスト状況などの追加情報を併記することを推奨します。