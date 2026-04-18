# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- 今後の変更予定をここに記載します。

## [0.1.0] - 2026-04-18
初回リリース

### Added
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）へ記録する。起動前に停止フラグ（data/stop_requested.flag）を確認し、PID ファイルを書き込む仕組みを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視用 DB 初期化と停止フラグ検出に対応。
- 設定管理 / ユーティリティ
  - config.py: Settings クラスを追加。環境変数のプロパティラッパー（J-Quants、kabu API、DBパス、監視しきい値、環境種別判定など）を提供。KABUSYS_ENV / LOG_LEVEL 等の値検証と便利プロパティ（is_live / is_paper / is_dev）を実装。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加。既存 .env の読み込み、秘匿項目のマスク表示、.env 書き出し機能あり。
  - validate_config.py: 起動前設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV の妥当性、DBパス・config/*.yaml の存在と YAML パース（PyYAML がある場合）を検証。--strict モードで警告を FAIL 扱いにできる。
  - .env 自動読み込み: プロジェクトルート（.git または pyproject.toml）を探索し、.env/.env.local を自動読み込み（既定）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ: export KEY=val 形式、クォート値（エスケープ対応）、インラインコメントルールなどに対応する堅牢なパーサを実装。
- ロギング / プロセス制御
  - utils/logging_setup.py: setup_logging を追加。ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定。既存ハンドラをクリアして再設定する。ログディレクトリ自動作成機能あり。
  - utils/process_priority.py: プロセス優先度設定ユーティリティを追加（Windows / POSIX 差分吸収）。set_cpu_affinity で CPU affinity 設定も可能。権限不足や未対応 OS の場合は安全にスキップして警告を出力。
- Execution コンポーネント（概念/API）
  - execution パッケージ内で BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、RiskManager、Reconciler 等の組立てロジックが利用されるフローを追加（run_execution からの起動を想定）。RiskManager のデフォルトパラメータ（max_position_pct 等）と初期ポートフォリオ値取得ロジックを導入。
- 監視・集計・レポート
  - monitoring.monitoring_db 初期化呼び出しを追加し、監視テーブルを確実に作成（冪等）。
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成 CLI を追加。稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL 判定を出力。期間フィルタ、DB パス指定オプション、P95 計算、閾値定義を実装。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: 候補選定 (select_candidates)、等重配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
  - portfolio/risk_adjustment: セクターキャップ適用 (apply_sector_cap)、レジームに基づく乗数計算 (calc_regime_multiplier) を実装。未知レジームではフォールバックと警告。
  - portfolio/position_sizing: position sizing ロジックを実装（risk_based / equal / score）。単元株（lot_size）丸め、1銘柄上限、aggregate cap によるスケーリング、cost_buffer を考慮した保守的見積り、スケール時の端数処理（remainder に基づく配分）などを備える。
- research/factor_research: DuckDB 接続を受け取りファクター（Momentum / Value / Volatility / Liquidity）を計算するための基礎を実装（設計コメントおよび定数群を追加）。※モジュールは続きを実装する設計。

### Changed
- ログ出力
  - ログの標準出力先を stderr から stdout に変更（cron/タスクスケジューラでの一元管理を想定）。
  - setup_logging が既存ハンドラを flush/close の上でクリアするようにして二重登録を防止。
- DB/環境の扱い
  - 監視（run_monitoring）は、KABUSYS_ENV に関わらず監視用 sqlite_path（settings.sqlite_path）を使用するように明示（設計上の注記）。
  - 実行系（run_execution）は paper_trading 環境時に paper_sqlite_path を優先して使用し、本番 DB と分離する。

### Fixed / Improved
- .env ロードの堅牢性
  - .env 読み込みで存在しないファイルを無視しつつ、読み込み失敗時は警告を出す（テストや権限問題に耐性）。
  - .env の上書き（override）処理で OS 環境変数を保護する protected 機構を導入（.env.local の上書き時に意図しない OS 環境変数の破壊を防止）。
- validate_config の改善
  - 必須環境変数のプレースホルダ検出（例: 値が "_here" や "your_value"）で警告を出す。
  - PyYAML 未インストール時に YAML 検証をスキップして警告を出力。
  - KABUSYS_ENV=live の場合に本番向けの注意喚起（LINE トークン未設定、KILL_FLAG_CLEAR_ON_START の危険性など）を追加。
- process_priority の堅牢化
  - 未対応 OS や権限不足の際に警告を出し、プロセスを継続させる設計に改善。

### Documentation
- 各モジュールに詳細な docstring と使用例、設計ノートを追加。config_setup と validate_config に CLI 使用方法を記載。
- portfolio / research モジュールに参照ドキュメント（PortfolioConstruction.md / StrategyModel.md 等）への言及を含め、設計意図を明示。

### Notes
- 停止制御はファイルベース（data/stop_requested.flag, data/kill.flag）で行う運用を前提としています。起動スクリプトはこれらのフラグを検出して安全に停止します。
- 一部モジュール（research calc 実装の続き等）は設計枠組みを整備しており、今後詳細実装が続きます。
- Breaking changes はありません（初回リリース）。

---

今後のバージョン管理では、機能追加は "Added"、互換性のある変更は "Changed"、バグ修正は "Fixed" を使ってこの CHANGELOG を更新してください。