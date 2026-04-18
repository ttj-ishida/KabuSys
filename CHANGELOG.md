Keep a Changelog
=================

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは「Keep a Changelog」仕様に準拠します。  
セマンティック バージョニングを使用します。

Unreleased
----------

（現在のスナップショットでは未リリースの変更は特になし）

[0.1.0] - 2026-04-18
-------------------

Added
- 初期リリース。KabuSys 自動売買フレームワークの基礎機能を追加。
- 実行系 / 監視系の起動スクリプトを追加:
  - run_execution: ExecutionEngine を起動するスクリプト。KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB（data/paper_trading.db）を使用し MockBrokerClient を利用する想定。起動時にプロセス優先度を "high" に設定。
  - run_monitoring: SystemMonitor のポーリングループを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能（デフォルト 60 秒）。停止フラグファイル（data/stop_requested.flag）を検知して終了。
- 環境設定・検証・ウィザード CLI を追加:
  - config_setup: 対話式ウィザードで .env を生成・更新するツール。
  - validate_config: .env と config/*.yaml の整合性チェックを行う検証ツール（--strict をサポート）。
- コンフィグ管理:
  - config.Settings クラスを導入。環境変数読み込みを統一管理（自動 .env ロード、保護キーの上書き制御など）。
  - .env パーサーは export プレフィックス、クォート文字列、インラインコメント（条件付き）を扱えるように実装。
  - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の検証とデフォルトを実装（不正値は例外または警告）。
- DB/分析基盤:
  - DuckDB（duckdb）接続を統合（Settings.duckdb_path）。
  - 監視用 SQLite（monitoring.db）および paper_trading 用 SQLite のパス管理。
  - init_monitoring_db 呼び出しで監視テーブルの存在を保証（冪等）。
- Execution コンポーネント群:
  - BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager（RiskConfig）を組み立てる起動フローを追加。
  - RiskConfig の既定値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定。initial_portfolio_value は BrokerClient の get_available_cash() を用いる。
  - エンジンは別スレッドで run_session を実行し、停止フラグで安全に停止可能。
- 監視（Monitoring）:
  - SystemMonitor を利用したポーリングループ、stop flag と pid ファイルの扱い、例外発生時のログとリトライ継続。
- ロギング・プロセス管理ユーティリティ:
  - utils.logging_setup.setup_logging: stdout（StreamHandler）と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。LOG_DIR/LOG_LEVEL の解決ロジックを実装。ログディレクトリ作成失敗時はファイル出力をスキップして継続。
  - utils.process_priority: Windows / POSIX に対応したプロセス優先度設定（high/normal/low）と set_cpu_affinity を提供。権限不足や未対応 OS の場合は警告を出してスキップ。
- ポートフォリオ構築（Portfolio）:
  - portfolio.portfolio_builder: シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合は等配分へフォールバック。
  - portfolio.risk_adjustment: セクター集中制限を行う apply_sector_cap と市場レジームに基づく乗数 calc_regime_multiplier を実装。未知のレジーム時には警告を出して 1.0 でフォールバック。
  - portfolio.position_sizing: 複数の allocation_method（risk_based / equal / score）で発注株数を算出。lot_size（単元）単位、1 銘柄上限、aggregate cap（available_cash）によるスケーリング、cost_buffer（手数料・スリッページ想定）を考慮した調整ロジックを実装。
- 解析 / ツール:
  - tools.paper_verification_report: Paper Trading 用 SQLite を読み、稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計して PASS/FAIL 判定を行うレポートを標準出力へ出力。しきい値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を設定。
- 研究（Research）:
  - research.factor_research にモメンタム等ファクター計算の骨子を追加（DuckDB 接続を受け prices_daily/raw_financials を参照）。（実装はページ途中まで含む）

Changed
- N/A（初期リリース）

Fixed / Robustness
- 環境変数の自動読み込みはプロジェクトルートが特定できない場合にスキップするようにして CWD に依存しない設計。
- .env 自動読み込み時、既存の OS 環境変数を保護（protected set）する仕組みを導入。
- MONITOR_POLL_INTERVAL 等の不正な環境変数値に対してデフォルトにフォールバックし、警告ログを出すようにして異常終了を回避。
- validate_config:
  - PyYAML 未インストール時は YAML 検証をスキップし、警告を出力。
  - 必須環境変数が未設定またはプレースホルダ値のままの場合はエラー/警告を出す。
- logging_setup:
  - ログディレクトリ作成失敗やファイルハンドラ生成失敗をハンドリングし、コンソール出力のみで継続するように安定化。

Security / Ops
- config_setup で生成される .env に対して「絶対に Git にコミットしないこと」という注意メッセージを明示。
- validate_config の live 環境向けガード（LINE 通知設定チェック、KILL_FLAG_CLEAR_ON_START の警告）を追加。

Known issues / Notes
- portfolio.risk_adjustment.apply_sector_cap: price が 0.0（欠損）だとエクスポージャーが過少見積りされる旨の TODO コメントあり。将来的にフォールバック価格の導入を検討。
- research.factor_research はファイル末尾が途中で切れている（calc_momentum の実装が途中）。研究モジュールは今後完成予定。
- 一部の機能は外部モジュール（psutil, duckdb, PyYAML 等）に依存する。これらが存在しない場合は機能限定または警告出力でフォールバックする設計。
- ログ・PID・フラグファイル等の既定パスは data/ や logs/ 以下に置かれる想定。運用環境では適切なディレクトリパーミッションを確認してください。

References
- See also: ソース内ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）への参照が多数含まれています（実ファイルはリポジトリに含まれる想定）。