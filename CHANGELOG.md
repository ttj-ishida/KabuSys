# Changelog

すべての変更は Keep a Changelog の方針に従って記載しています。  
日付はリリース日を示します。

フォーマットの説明と慣例:
- Added: 新機能
- Changed: 既存挙動の変更（後方互換性があるもの）
- Fixed: バグ修正
- Removed / Deprecated / Security: 該当があれば記載

## [Unreleased]

## [0.1.0] - 2026-04-17
初回リリース。KabuSys 自動売買フレームワークの基本機能群を追加。

### Added
- 全体
  - パッケージバージョンを設定（kabusys.__version__ = "0.1.0"）。
  - DuckDB と SQLite を組み合わせたデータ管理基盤の導入（デフォルトパス: data/kabusys.duckdb, data/monitoring.db）。
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper-trading SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と分離。
    - BrokerClientFactory を使って環境に応じたブローカークライアントを生成（モック/実ブローカーの切替え）。
    - ExecutionEngine を別スレッドで実行し、stop flag（data/stop_requested.flag）を検知して安全に停止可能。
    - 起動時にプロセス優先度を "high" に設定。
    - PID ファイルパスを管理（data/execution.pid をデフォルトで使用）。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する実装。
    - stop flag（data/stop_requested.flag）でループ終了。
    - 起動時にプロセス優先度を "high" に設定。
- 設定関連
  - config.py: 環境変数読み込み・管理クラス（Settings）を追加。
    - .env 自動読み込み機能（プロジェクトルートを .git / pyproject.toml から検出）。
    - 複数の設定プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE 等）を提供。
    - KABUSYS_ENV, LOG_LEVEL 等の妥当性チェック（許容値の検証）。
    - paper_sqlite_path, pid_file_path, kill_flag_path, 各種閾値（CPU/MEM/DISK）をプロパティ経由で取得。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - デフォルト値、選択肢、シークレット入力、既存 .env の読み込み・再利用に対応。
    - 生成時に .env のテンプレートを出力（コミット禁止の注意を付記）。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と YAML パース検証（PyYAML があればパース検証を実行）を実施。
    - --strict モードで警告を FAIL 扱いにできる。
    - 本番（KABUSYS_ENV=live）向けの追加ガード（LINE 設定・KILL_FLAG_CLEAR_ON_START の確認）を実装。
- ポートフォリオ構築（pure functions）
  - portfolio/portfolio_builder.py
    - select_candidates: シグナルのスコア降順選定（同点の tiebreaker: signal_rank）。
    - calc_equal_weights, calc_score_weights: 等配分・スコア加重配分を提供（スコア全て 0 の場合は等配分にフォールバックし警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限（max_sector_pct）を適用して候補を除外するロジック。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を返す（unknown レジームはフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: 重み・候補・ポートフォリオ状態を元に発注株数を計算する主要ロジックを実装。
      - allocation_method 支持: "risk_based", "equal", "score"。
      - lot_size（単元株）丸め、max_position_pct（1銘柄上限）、max_utilization（投下資金上限）、cost_buffer（手数料・スリッページ補正）を考慮。
      - aggregate cap 超過時はスケーリングと残差処理（lot 単位での再配分）を実装。
- Utils
  - utils/process_priority.py: プロセス優先度と CPU affinity のユーティリティを追加。
    - Windows / POSIX の差分を吸収して set_process_priority(level) を提供（"high"/"normal"/"low"）。
    - set_cpu_affinity(cpu_count) でプロセスを先頭 N コアにピン留め可能（失敗時は警告でスキップ）。
    - 権限不足や未対応プラットフォームに対しては安全に警告を出して処理をスキップする実装。
- モニタリング / 実行補助
  - monitoring.monitoring_db.init_monitoring_db の呼び出しにより監視テーブルの準備を起動時に保証（冪等）。
  - Execution 側で RiskManager のデフォルト設定値を明示（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
  - Reconciler / OrderManager / OrderRepository 等の組立てロジックを run_execution で行い、ExecutionEngine を起動する流れを提供。
- リサーチ
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールを追加（Momentum, Volatility, Liquidity 等）。
    - calc_momentum, calc_volatility 等の関数を実装（指定日付のモメンタム・MA200乖離・ATR 等を計算）。
    - DuckDB の SQL を活用して高速に集計。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを集計して PASS/FAIL 判定を出力。
    - CLI オプションで期間（--from / --to）と DB パス（--db）を指定可能。
    - デフォルトの判定閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）。
- ドキュメント・設計ノート（コード内コメント）
  - PortfolioConstruction.md / StrategyModel.md 等を参照する設計注釈が関数ドキュメントに含まれている（実装意図の明記）。

### Changed
- .env 自動読込
  - プロジェクトルートを __file__ を基点に辿る方式を採用し、CWD に依存しない自動ロードを実装。
  - OS 環境変数を保護するため protected キーセットを導入（.env 読み込み時の上書き制御）。
- 環境変数パーサ
  - _parse_env_line により引用符付き値、エスケープ、インラインコメントの扱いを厳密化し、.env の柔軟な記述に対応。

### Fixed
- 起動・停止制御
  - run_execution/run_monitoring において stop flag（data/stop_requested.flag） を検知して安全に終了・停止する仕組みを整備。
  - run_execution で停止要求を検知した際に ExecutionEngine.stop() を呼び出してセッションを中断する流れを確実化。

### Notes / Migration
- デフォルトのファイルパス（data/ 以下）や環境変数名はコード中にハードコードされています。デプロイ時は .env または環境変数で適切に上書きしてください。
- .env は絶対に Git にコミットしないでください（config_setup の注意書きを参照）。
- KABUSYS_ENV に `live` を設定する場合は validate_config を用いてすべての設定（特に LINE 通知・KILL_FLAG_*）を慎重に確認してください。
- PAPER_FILL_MODE の値は "instant" | "partial" | "never" | "reject" のいずれかである必要があります（不正値は起動時に ValueError）。

---

今後のリリースでは以下を予定しています（例）:
- ExecutionEngine / Broker 実装の追加テスト、戦略モジュールの統合、戦略パラメータの YAML 化、CI テストの整備、単体テスト充実。

もし CHANGELOG に含めてほしい特定の変更点や別の日付での記載があれば教えてください。