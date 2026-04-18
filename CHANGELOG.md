# Changelog

すべての注目すべき変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。
このプロジェクトはセマンティックバージョニングを採用します。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-18
初回リリース。主要な機能群とユーティリティを実装しました。

### 追加 (Added)
- コアパッケージ
  - kabusys パッケージを導入。バージョンは `0.1.0`。
- 設定管理
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - 複雑な .env 行パースに対応（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理）。
  - 環境変数保護（OS 環境変数を上書きしない仕組み）および自動読み込み無効化用フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
  - Settings クラスを実装し、J-Quants / kabu API / DB パス /監視閾値 / 環境種別などの設定プロパティを提供。
  - `PAPER_FILL_MODE`, `PAPER_TRADING_SQLITE_PATH`, `KILL_FLAG_CLEAR_ON_START` 等の環境変数サポートと入力検証。
- 設定ユーティリティ / CLI
  - `kabusys.config_setup`：対話式ウィザードで .env を作成・更新する CLI を実装。既存値の再利用、シークレットマスク、生成ファイルヘッダを備える。
  - `kabusys.validate_config`：起動前に .env と config/*.yaml の妥当性を検証する CLI を実装。`--strict` オプションで警告をエラー扱いにできる。YAML のパースは PyYAML がインストールされている場合に実施。
- ロギング
  - `kabusys.utils.logging_setup.setup_logging`：標準出力（stdout）への StreamHandler と、日次ローテーション（TimedRotatingFileHandler、30日保持）のファイル出力をルートロガーに設定するユーティリティを実装。LOG_DIR / LOG_LEVEL の環境変数を尊重。
  - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールログのみで継続する堅牢性。
- プロセス制御ユーティリティ
  - `kabusys.utils.process_priority`：Windows / POSIX を吸収してプロセス優先度（high/normal/low）を設定する機能を実装。CPU affinity を設定する `set_cpu_affinity` も提供。権限不足等の失敗は警告でフォールバック。
- Execution / Monitoring 起動スクリプト
  - `run_execution.py`：
    - `ExecutionEngine` の起動スクリプト。プロセス優先度を最初に設定。
    - `KABUSYS_ENV=paper_trading` の場合は paper 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と明確に分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine のバックグラウンドスレッド起動、停止フラグ（data/stop_requested.flag）監視、PID ファイル管理。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義。初期ポートフォリオ値を broker.get_available_cash() から取得。
  - `run_monitoring.py`：
    - `SystemMonitor` を用いたポーリングループの起動スクリプト。プロセス優先度を設定し、sqlite と duckdb に接続。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 監視は常に（環境にかかわらず）本番 sqlite_path を使用して監視データを記録する設計。
- 監視 DB 初期化
  - `monitoring.monitoring_db.init_monitoring_db` を呼び出して監視用テーブルの存在を保証（冪等）。
- ポートフォリオ構築ライブラリ
  - `kabusys.portfolio.portfolio_builder`：
    - 候補選定 `select_candidates`（スコア降順、同点は signal_rank をタイブレーク）。
    - 重み計算 `calc_equal_weights`, `calc_score_weights`（スコア合計が 0 の場合は等配分へフォールバック）。
  - `kabusys.portfolio.risk_adjustment`：
    - セクター集中制限 `apply_sector_cap`（既存保有を基にセクター別エクスポージャを算出して候補を除外、"unknown" セクターは上限未適用）。
    - レジーム乗数 `calc_regime_multiplier`（bull/neutral/bear のマッピングと未知レジームは 1.0 にフォールバック）。
  - `kabusys.portfolio.position_sizing`：
    - `calc_position_sizes`：risk_based / equal / score の配分方式に対応。単元株（lot_size）で丸め、max_position_pct・max_utilization・cost_buffer を考慮した aggregate cap（全体スケーリング）を実装。cash が不足する場合のスケールダウンと残差配分ロジックを実装。
- 解析・研究ユーティリティ
  - `kabusys.research.factor_research`（ファクター計算モジュール）：
    - Momentum / Value / Volatility / Liquidity 等のファクター算出方針を実装（DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計）。
- ツール
  - `kabusys.tools.paper_verification_report`：Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（P95）等を集計して PASS/FAIL を判定する。閾値（稼働率 99%、成功率 90%、送信率 95%、P95 200ms）を定義。CLI オプションで期間指定（--from / --to）と DB パス上書き (--db) に対応。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 削除 (Removed)
- なし（初回リリース）

### セキュリティ (Security)
- .env 自動読み込み時に OS 環境変数を上書きしないよう保護セットを導入（保護されたキーは .env で上書きされない）。
- 自動読み込みを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` オプションを用意（テスト等で利用可能）。

---

注:
- デフォルトのパスや設定値:
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring): data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
  - ログディレクトリ: logs/
  - デフォルトポーリング間隔: 60 秒
- 実行例:
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Execution 起動: python -m kabusys.run_execution
  - Monitoring 起動: python -m kabusys.run_monitoring
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

もし CHANGELOG にさらに詳しい項目（例えば個々の関数実装の詳細や既知の問題点）を追加したい場合はお知らせください。