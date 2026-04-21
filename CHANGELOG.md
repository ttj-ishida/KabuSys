# CHANGELOG

すべての重要な変更点を Keep a Changelog のフォーマットに準拠して記載します。  
このファイルはリポジトリのコードベースから機能・挙動を推測して作成しています。

フォーマットの説明: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-21

初回リリース。日本株自動売買システム「KabuSys」のコアユーティリティ、起動スクリプト、ポートフォリオ構築、検証ツール、設定管理など一通りの機能を提供します。

### Added
- パッケージ初期化
  - `kabusys.__version__ = "0.1.0"` を追加。

- 起動スクリプト
  - `run_execution.py`
    - ExecutionEngine を起動するエントリポイントを実装。
    - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を利用し paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用することで本番 DB と分離する仕組みを提供。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority を利用）。
    - 停止フラグファイル（data/stop_requested.flag）と実行 PID ファイル（data/execution.pid）を用いた停止・監視機構。
    - ExecutionEngine はスレッドで実行され、停止フラグ検出時に engine.stop() を呼び出して安全終了を試みる。

  - `run_monitoring.py`
    - SystemMonitor のポーリングループ用エントリポイントを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックし警告を出力。
    - 監視は環境にかかわらず本番用の sqlite_path を使用する（監視データは本番側 DB を参照する仕様）。
    - 停止フラグファイル（data/stop_requested.flag）によるループ終了検出と KeyboardInterrupt ハンドリングを実装。

- 設定管理・読み込み
  - `config.py`
    - 環境変数 / .env 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - .env の読み込み順序: OS 環境 > .env.local > .env。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能（テスト用）。
    - .env 行のパースは `export KEY=val`、クォート（シングル/ダブル）、エスケープ、インラインコメントの取り扱いをサポート。
    - `Settings` クラスを提供し、各種設定（API トークン、DB パス、PID / Kill flag のパス、監視閾値、環境種別フラグなど）をプロパティとして取得可能。
    - `PAPER_FILL_MODE` の検証（有効値: "instant"|"partial"|"never"|"reject"）や `KABUSYS_ENV` の検証（"development"|"paper_trading"|"live"）を実装。

  - `config_setup.py`
    - 対話式ウィザードで .env を生成・更新する CLI を実装。
    - デフォルト値、選択肢、シークレット入力のマスク、既存 .env の読み込み・再利用機能を提供。
    - 生成した .env の保存と次の検証手順の案内を表示。

  - `validate_config.py`
    - 起動前に .env および config/*.yaml の基本的な妥当性をチェックする CLI を実装。
    - 必須環境変数の未設定チェック、プレースホルダ値検出、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML がインストールされている場合）を行う。
    - `--strict` オプションで警告を FAIL 扱いにする機能。

- ロギングユーティリティ
  - `utils/logging_setup.py`
    - 全起動スクリプトで統一的に利用できるログ設定関数 `setup_logging(app_name, log_dir, level)` を実装。
    - コンソール出力は stdout（標準出力）へ出すことで Task Scheduler/cron 等での stdout/stderr リダイレクトに対応。
    - 日次ローテーション（TimedRotatingFileHandler）でログファイルを出力し、30 日分を保持。
    - ログディレクトリの作成失敗を許容し、その場合はコンソール出力のみで継続。

- プロセス優先度 / CPU 固定ユーティリティ
  - `utils/process_priority.py`
    - Windows / POSIX（Linux, macOS, FreeBSD）で差分を吸収してプロセス優先度（nice / Windows priority class）を設定する `set_process_priority(level)` を実装。
    - CPU affinity を設定する `set_cpu_affinity(cpu_count)` を提供（実行環境によっては権限不足で失敗した際に警告を出力してスキップ）。
    - 許容レベル: "high" / "normal" / "low"。

- ポートフォリオ構築（純粋関数群）
  - `portfolio/portfolio_builder.py`
    - 候補選定 `select_candidates(buy_signals, max_positions)`（スコア降順、同点は signal_rank 昇順でタイブレーク）。
    - 等重み `calc_equal_weights(candidates)`、スコア加重 `calc_score_weights(candidates)`（全スコアが 0 の場合は等重みにフォールバック）を実装。

  - `portfolio/risk_adjustment.py`
    - セクター集中制限 `apply_sector_cap(...)` を実装。既存保有のセクター比率に基づいて当日新規候補を除外。
    - 市場レジームに応じた投下資金乗数 `calc_regime_multiplier(regime)` を実装（"bull":1.0, "neutral":0.7, "bear":0.3。未知レジームは警告して 1.0 フォールバック）。

  - `portfolio/position_sizing.py`
    - 発注株数計算 `calc_position_sizes(...)` を実装。
    - allocation_method に応じた計算（"risk_based" / "equal" / "score"）と、単元株（lot_size）での丸め処理、1 銘柄上限・総投下上限の適用。
    - コストバッファ（slippage/commission 見積り）を考慮した aggregate cap と、スケールダウン後の残差を基に lot_size 単位で追加配分するアルゴリズムを実装。

- Execution 関連コンポーネント（起動スクリプトから組み立てられる）
  - BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager（`RiskConfig`）など実行に必要なコンポーネント群を参照して組み立てるコードを起動スクリプトで統合。
  - `RiskConfig` のデフォルト値を設定（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）。
  - RiskManager の初期ポートフォリオ値取得に broker.get_available_cash() を利用。

- 監視データベース初期化
  - `monitoring/monitoring_db.init_monitoring_db` を利用して監視用テーブルの存在を保証（冪等性）。

- Paper Trading 検証ツール
  - `tools/paper_verification_report.py`
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から指標を集計し、PASS/FAIL 判定を行う CLI を実装。
    - 指標: 稼働率 (uptime)、注文成功率（fill rate）、送信率（send rate）、API レイテンシ（avg/max/P95）など。
    - デフォルト基準値を定義（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 レイテンシ <= 200 ms）。
    - P95 計算ユーティリティ、期間フィルタ、DB 存在チェックなどを備える。

- 研究用ファクターモジュール（部分実装）
  - `research/factor_research.py`
    - DuckDB を利用して定量ファクター（Momentum、Value、Volatility、Liquidity 等）を計算する設計を追加。
    - モメンタム計算用の定数と関数インターフェース（calc_momentum(conn, target_date)）を導入（ファイル末尾は計算ロジックの実装が続く設計）。

### Changed
- なし（初期リリースのため、過去からの変更はなし）

### Fixed
- なし（初期リリースのため、既知のバグ修正はなし）

### Security
- なし

### Notes / Usage tips
- .env 自動ロードはプロジェクトルートが検出できない場合はスキップされます（パッケージ配布後でも cwd に依存しないように実装）。
- `.env` の自動上書きは OS 環境変数を保護する設計（protected set）になっており、`.env.local` は `.env` の値を上書き可能。
- ログはデフォルトで stdout に流し、ファイル出力は logs/<app_name>.log に日次ローテーションで保存（ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみ）。
- process priority / CPU affinity の設定は権限不足や未対応 OS の場合は警告を出して安全にスキップします。
- 監視（monitoring）は監視用 DB を参照する設計で、監視プロセス自体は環境にかかわらず sqlite_path を使用します。Execution は paper_trading 時に専用 DB を使用して本番 DB と分離します。

---

今後のリリースでは、実装済みコンポーネントの単体テスト追加、factor_research の完全実装、ExecutionEngine 周りの詳細なエラー処理・再試行戦略や CLI ドキュメント強化を予定してください。