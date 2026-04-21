# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  
<https://keepachangelog.com/ja/1.0.0/>

## [0.1.0] - 2026-04-21

### Added
- 初期リリース。KabuSys 自動売買システムのコアユーティリティ群と CLI / スクリプトを追加。
  - パッケージメタ情報
    - src/kabusys/__init__.py にバージョン情報 `__version__ = "0.1.0"` を追加。

  - 起動スクリプト
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
      - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視 DB は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する実装。
      - 停止はプロジェクトルート/data/stop_requested.flag によるフラグ検出で行う。
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。
      - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用して paper_trading 専用 DB（デフォルト: data/paper_trading.db）に記録し、本番 DB と完全分離。
      - 実行中の PID 管理用ファイルおよび停止フラグ管理（data/execution.pid, data/stop_requested.flag）。
      - ExecutionEngine を別スレッドで実行し、停止フラグで安全に停止するループを実装。

  - 設定管理・ウィザード・検証
    - config.py: 環境変数からの設定読み取りを行う Settings クラスを実装。
      - .env 自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。
      - .env の自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD` によって無効化可能。
      - 各種プロパティを提供（J-Quants / kabu API / DB パス / paper_trading 用設定 / 監視閾値 / 環境判定等）。
      - `PAPER_FILL_MODE` のバリデーション、`PAPER_TRADING_SQLITE_PATH` などのデフォルトや expanduser 対応。
    - config_setup.py: 対話式 .env 作成・更新ウィザードを実装。
      - シークレット入力をマスク表示、既存 .env の読み込みと Enter による再利用、ファイル書き出し。
      - 初期項目セット（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 等）。
    - validate_config.py: 起動前の設定検証 CLI を追加。
      - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在とパース検証（PyYAML 未導入時はスキップ）等。
      - `--strict` モードで警告を FAIL 扱いに可能。

  - ロギング / プロセス制御ユーティリティ
    - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。
      - StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定。
      - 環境変数 `LOG_LEVEL` / `LOG_DIR`、引数 `level` / `log_dir` で上書き可能。
      - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - utils/process_priority.py: プロセス優先度（および CPU affinity）設定ユーティリティを追加。
      - Windows/Linux/macOS の差を吸収して `set_process_priority(level)` を提供（"high"/"normal"/"low"）。
      - `set_cpu_affinity(cpu_count)` でプロセスを最初の N コアに固定可能（Linux/macOS 等対応）。
      - psutil を用い、権限不足などは警告でスキップ。

  - ポートフォリオ構築（純粋関数）
    - portfolio/portfolio_builder.py:
      - select_candidates: スコア降順で候補選定（タイブレークに signal_rank を使用）。
      - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコア全 0 の際は等金額へフォールバック）。
    - portfolio/risk_adjustment.py:
      - apply_sector_cap: セクター集中上限チェック（既存保有比率に基づき新規候補を除外）。
      - calc_regime_multiplier: market regime に応じた資金乗数（bull/neutral/bear をマッピング、未知値は警告の上 1.0 にフォールバック）。
    - portfolio/position_sizing.py:
      - calc_position_sizes: 重み・候補・現金・既存ポジション・価格等から発注株数を計算。risk_based / equal / score の配分方式に対応。
      - 単元株丸め、最大ポジション上限、aggregate cap（利用可能現金によるスケーリング）、コストバッファ考慮、残差に応じた追加配分ロジックを実装。

  - Paper Trading 向けツール
    - tools/paper_verification_report.py:
      - Paper Trading の検証レポート生成スクリプトを追加（SQLite DB を解析して稼働率、注文成功率、送信率、レイテンシ等を評価）。
      - P95 計算、期間フィルタ、基準値による PASS/FAIL 判定（閾値はソース内定義）。
      - CLI オプション: --from / --to / --db、環境変数 `PAPER_TRADING_SQLITE_PATH` を解釈。

  - リサーチ / ファクター計算（基礎）
    - research/factor_research.py:
      - DuckDB を用いたモメンタム / ボラティリティ / 流動性 / バリュー等のファクター計算方針といくつかの定数を追加（モジュール設計）。
      - calc_momentum 等の実装を開始（ファイル末尾で実装が続く構成）。

  - DB 初期化ヘルパ
    - monitoring/monitoring_db.init_monitoring_db を複数起動スクリプトから呼び出して監視テーブルの存在を保証（冪等）。

### Changed
- （初期リリースのため変更履歴なし）

### Fixed
- （初期リリースのため修正履歴なし）

### Security
- （現時点で該当なし）

注:
- 各スクリプト・ユーティリティは可能な限り OS や実行環境の差分を吸収する設計になっていますが、実行環境によっては権限や未インストールライブラリ（例: psutil / PyYAML / duckdb）に依存します。運用前に validate_config や config_setup を実行して設定・依存関係を確認してください。