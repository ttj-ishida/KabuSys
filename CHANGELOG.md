# Changelog

すべての変更は「Keep a Changelog」形式に準拠しています。主にコードベース（src/ 以下）の初期実装・機能追加を反映しています。

## [Unreleased]

## [0.1.0] - 初回リリース
最初の公開リリース。システム監視、実行エンジン起動スクリプト、設定管理、ポートフォリオ構築、リスク調整、ポジションサイズ計算、ファクター計算ツールなどの主要コンポーネントを提供します。

### Added
- CLI / 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告してデフォルトにフォールバック。
    - 停止フラグ（data/stop_requested.flag）検出による優雅な終了処理。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番の sqlite_path を使用。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を利用して data/paper_trading.db に記録し、本番 DB と分離。
    - 起動時に data/execution.pid を利用する仕組み、停止フラグの検出でエンジン停止。
- 設定関連
  - config.py: .env 自動読み込み・パースロジックと Settings クラスを提供。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）により CWD に依存しない読み込み。
    - .env/.env.local の読み込み順・上書きルール（OS 環境変数保護）を実装。
    - 多数のプロパティ（DB パス、API トークン、監視閾値、環境判定等）を提供。
    - PAPER_FILL_MODE の厳格な検証（allowed: "instant","partial","never","reject"）。
  - config_setup.py: 対話式 .env ウィザードを追加（.env の初期作成・更新を支援）。
  - validate_config.py: 設定検証ツールを追加（.env と config/*.yaml の検証、--strict オプション）。
- 監視 DB 初期化ユーティリティ（monitoring_db への依存をコードから利用）。
- Portfolio（ポートフォリオ構築）モジュール
  - portfolio_builder.py:
    - select_candidates: スコア順選抜（タイブレークに signal_rank）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（全銘柄スコア 0 の場合は等金額へフォールバック）。
  - risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェック（売却予定銘柄を除外するオプション、"unknown" セクターは除外しない）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数。
  - position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数計算、単元株（lot_size）丸め、aggregate cap（available_cash）に基づくスケーリングと残余配分ロジックを実装。
- Research（ファクター計算）
  - factor_research.py: DuckDB を用いたファクター計算ユーティリティ（例: calc_momentum, calc_volatility）。prices_daily テーブルからモメンタム・ATR・出来高指標等を計算。
- ユーティリティ
  - utils/process_priority.py:
    - set_process_priority: Windows / POSIX（Linux, Darwin, FreeBSD）に対応してプロセス優先度を設定。未対応 OS ではスキップ。
    - set_cpu_affinity: 指定コア数にプロセスをピン留め。権限不足や未実装 API を適切にハンドルして警告。
- Tools
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成ツールを追加。稼働率、注文成功率、送信率、P95 レイテンシなどを集計し PASS/FAIL 判定を実施。
- DuckDB 統合
  - DuckDB 接続を分析用途（ファクター計算、ExecutionEngine 内部分析など）で利用する実装を追加（Settings.duckdb_path 参照）。

### Changed
- なし（初回リリースのため新規追加中心）。

### Fixed / Robustness improvements
- .env パーサーの強化（config._parse_env_line）
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメントの正しい扱い、クォートなしでの '#' によるコメント判定など堅牢に実装。
- run_monitoring.py:
  - MONITOR_POLL_INTERVAL の不正値（非数、0 以下）を検出し、警告してデフォルトにフォールバックするようにして time.sleep の ValueError を防止。
  - check_once() 実行中の例外を捕捉してログ出力し、ポーリングループを継続する耐障害性を追加。
- process_priority: 権限不足や未実装 API（psutil の例外）を捕捉して警告ログとともにスキップすることで、起動失敗を防止。
- calc_score_weights: 全スコアが 0 の場合に等金額配分へ安全にフォールバック（警告ログ）。
- calc_regime_multiplier: 未知のレジーム値で警告を出して 1.0 にフォールバック。
- position_sizing: aggregate cap 適用時のスケーリングと単元丸めにおいて、残余キャッシュを用いた端数配分ロジックを導入し再現性を確保（安定ソート）。

### Security
- .env ファイル生成テンプレート（config_setup._write_env）に注意喚起コメントを記載（.env を Git にコミットしないよう明記）。

### Notes / Operational details
- Paper trading と本番 DB は分離（Settings.paper_sqlite_path / PAPER_TRADING_SQLITE_PATH）。
- 起動時に Kill/Stop フラグ（data/stop_requested.flag や data/kill.flag）や PID ファイル（data/execution.pid）を用いてプロセス制御・安全停止を行う設計。
- validate_config.py は PyYAML が未インストールでも動作し、YAML の検証をスキップして警告を出力する。
- run_execution は BrokerClientFactory を利用して環境に応じたブローカークライアント（Mock/実ブローカー）を生成する想定。

---

開発者向けメモ:
- 今後のリリースでは、テストカバレッジ、エラー監視（外部通知）、設定値のより厳密な検証、銘柄別 lot_size のサポート、価格欠損時のフォールバック戦略（price_map の欠損対応）などを検討してください。