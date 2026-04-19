# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-19
初回リリース。KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、検証/設定ツール、および Paper Trading 検証ツールを実装しました。

### Added
- 全体
  - パッケージ初期化とバージョン定義を追加（src/kabusys/__init__.py, __version__ = "0.1.0"）。
  - DuckDB / SQLite を併用するデータレイヤ設計を導入（設定でパス指定可能）。

- 設定 / 環境変数
  - Settings クラスを追加（src/kabusys/config.py）。
    - .env の自動ロード機能（プロジェクトルート検出、.env / .env.local の読み込み順）を実装。
    - J-Quants / kabuステーション / LINE / DB / 監視閾値 / システム設定等のプロパティを提供。
    - 環境変数の妥当性チェック（KABUSYS_ENV, LOG_LEVEL 等）を実装。
    - PAPER_FILL_MODE（paper trading の fill 挙動）や PAPER_TRADING_SQLITE_PATH 等の paper_trading 用設定をサポート。
  - .env ファイルの行パーサー実装（クォート内エスケープ、export プレフィックス、インラインコメント処理に対応）。

- 設定支援 CLI
  - 対話式環境設定ウィザードを追加（src/kabusys/config_setup.py）。
    - .env の初期作成・更新をサポート。秘密値はマスク表示。
    - 保存用ヘッダ、推奨デフォルト値を出力。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数・KABUSYS_ENV・ログレベル・DBパス・config/*.yaml の存在/パース（PyYAML があれば）を検査。
    - --strict オプションで警告を FAIL 扱いにする機能を追加。
    - 本番環境（KABUSYS_ENV=live）向けガード（LINE 設定、KILL_FLAG_CLEAR_ON_START の注意喚起）を追加。

- 起動スクリプト / 実行コンポーネント
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は専用の Paper DB を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成を利用（MockBroker 対応）。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立て ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）による制御。
    - スレッドで実行し、停止フラグ検知時に engine.stop() で終了処理。
    - RiskManager のデフォルト構成（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定し、初期ポートフォリオ値は broker.get_available_cash() から取得。

  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - SystemMonitor のチェックループを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。
    - 監視は環境に関わらず本番用 sqlite_path を使用する挙動を明記。
    - stop フラグファイル検知でループを終了、KeyboardInterrupt による終了に対応。
    - DuckDB との接続管理と監視 DB 初期化呼び出しを行う。

- ロギング / プロセス管理ユーティリティ
  - 統一ログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout への StreamHandler（stdout を利用）と日次ローテートする TimedRotatingFileHandler（logs/<app_name>.log、30日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR / 引数レベルの優先ルールを実装。
    - ログディレクトリ作成失敗時はファイル出力を自動で無効化（コンソールのみ）する耐障害性。
  - プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - psutil を利用して Windows / POSIX に対応する優先度（high/normal/low）設定を行う set_process_priority()。
    - set_cpu_affinity() により最初の N コアにプロセスをピン留めする機能。
    - 設定失敗（権限不足等）は警告ログを出してスキップ。

- ポートフォリオ構築ロジック（純粋関数群）
  - 銘柄選定・重み付け（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順・タイブレークを signal_rank で行う。
    - calc_equal_weights / calc_score_weights: スコア正規化・スコアが全て 0 の場合は等重でフォールバック。
  - セクター制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター比率に基づき新規候補を除外。unknown セクターは制限対象外。
    - calc_regime_multiplier: レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバックし警告ログ。
  - 株数決定・リスク制限（src/kabusys/portfolio/position_sizing.py）
    - allocation_method に応じた株数計算（risk_based / equal / score）。
    - risk_based: risk_pct / stop_loss_pct に基づくポジションサイズ算出。
    - per-position 上限（max_position_pct）、aggregate 上限（available_cash）を尊重。
    - 単元株（lot_size）丸め処理、cost_buffer を用いた保守的コスト見積り。
    - aggregate cap 超過時のスケーリングと端数（lot 単位）再配分ロジックを実装。

- Paper Trading / 検証ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - DB から system_status / trade_logs / risk_logs を集計し、稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）等を計算。
    - P95 計算、日付フィルタ（--from, --to）、--db オプション対応。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）に基づく PASS / FAIL 判定を出力。

- データ研究モジュール（骨格）
  - ファクター計算モジュールの骨格を追加（src/kabusys/research/factor_research.py）。
    - Momentum / Value / Volatility / Liquidity の設計方針と定数を定義。
    - calc_momentum の実装開始（内部には DuckDB を使った prices_daily 参照を想定）。※ 実装途中で断片が含まれます。

### Changed
- なし（初回リリースのため該当なし）。

### Fixed
- .env 読み込み時のエラーハンドリングを改善（読み込み失敗時に warnings.warn 出力）。
- logging_setup:
  - ログディレクトリ作成失敗時のフォールバックを明示的に扱うようにし、FileHandler 作成に失敗してもプロセスは継続する耐障害性を追加。

### Deprecated
- なし

### Removed
- なし

### Security
- なし（秘匿値は .env で管理すること、.env を Git にコミットしない旨をドキュメント / config_setup のヘッダに明記）。

---

注記 / 運用メモ
- 監視 / 実行の停止はプロジェクトルート直下の data/stop_requested.flag を作成して行います。execution は data/execution.pid を PID 管理に使用します。
- 設定検証（python -m kabusys.validate_config）や設定ウィザード（python -m kabusys.config_setup）を起動前に利用してください。
- Paper Trading と Live は DB を分離しているため、テスト・検証時に本番 DB を汚染しません（PAPER_TRADING_SQLITE_PATH を上書き可能）。
- logfile はデフォルトで logs/<app_name>.log に日次ローテートで保存されます。LOG_DIR 環境変数で変更可能です。

もし特定ファイルの変更差分（行レベル）や今後のリリースノート雛形が必要であれば、その対象を指定して下さい。