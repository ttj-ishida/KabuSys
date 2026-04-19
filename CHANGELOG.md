CHANGELOG
=========

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。
リリース方針: 互換性の破壊的変更は Breaking changes として明示します。

[Unreleased]
-------------

（現在のリポジトリは初期リリース相当の内容が含まれているため、本ファイルでは直近のリリースを下に記載しています。）

[0.1.0] - 2026-04-19
-------------------

初回公開リリース。システム全体の起動スクリプト、設定管理、監視、実行エンジン起動のユーティリティ、ポートフォリオ構築ロジック、分析/検証ツールなどの基盤機能を実装しました。

### Added
- 基本パッケージ情報
  - パッケージバージョンを設定: kabusys.__version__ = "0.1.0"

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。プロセス優先度設定、SQLite/DuckDB 接続、Paper Trading 用の DB 分離、停止フラグ（data/stop_requested.flag）や実行 PID ファイル (data/execution.pid) に基づく制御を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は常に本番用 sqlite_path を使用する設計。

- 設定管理 / 初期化
  - config.py: 環境変数/ .env の読み込み・解釈ロジックを実装。プロジェクトルート自動検出（.git または pyproject.toml）、.env/.env.local の自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）、設定値の型チェックや検証付きプロパティ（例: PAPER_FILL_MODE の検証、KABUSYS_ENV / LOG_LEVEL のバリデーション）を提供。
  - config_setup.py: .env を対話的に生成・更新するウィザードを追加。各種設定項目（J-Quants トークン、kabu API パスワード、DB パス、ログレベルなど）を対話的に入力し .env に保存。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在および（PyYAML があれば）パース検証、live 環境向けの安全ガード（LINE 設定未設定や Kill Switch 自動クリアの警告）を実装。--strict オプションで警告を FAIL 扱いにできる。

- 実行系コンポーネントの組み立て
  - execution/ 以下（EngineConfig, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager, BrokerClientFactory 等）を想定した起動処理を実装（run_execution.py からの組み立てを実現）。RiskManager に既定の RiskConfig を与える例を含む（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）。Paper Trading 時は専用の SQLite（data/paper_trading.db がデフォルト）を使用し、本番 DB と分離する設計。

- 監視機能
  - monitoring 側初期化（init_monitoring_db 呼び出し）を起動スクリプトで担保。monitoring の DB は環境に依存せず本番 sqlite_path を使用する仕様。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py: 共通ログ設定ユーティリティを追加。コンソール出力（stdout）用 StreamHandler と 日次ローテートする TimedRotatingFileHandler（デフォルト logs/ ディレクトリ、30 日保持）をルートロガーに設定。ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソールのみで継続。
  - utils/process_priority.py: Windows/Linux/macOS を吸収するプロセス優先度設定ユーティリティを追加。set_process_priority("high"|"normal"|"low")、set_cpu_affinity(n) を提供。アクセス権限不足や未対応 OS の場合は警告を出してスキップ。

- ポートフォリオ構築ライブラリ（純関数群）
  - portfolio/portfolio_builder.py: シグナルから候補選定（select_candidates）と重み計算（calc_equal_weights, calc_score_weights）を実装。スコアが全て 0 の場合は等配分へフォールバックし警告を出力。
  - portfolio/risk_adjustment.py: セクター集中上限適用（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知のレジームはフォールバック値を返す。
  - portfolio/position_sizing.py: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算を実装。単元株丸め、1 銘柄上限、aggregate cap（利用可能現金に基づくスケールダウン）、cost_buffer を考慮したスケーリング処理を含む。

- 分析 / 検証ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。system_status, trade_logs, risk_logs テーブルから稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計し、PASS/FAIL を出力する。閾値（稼働率 99%、成功率・送信率の基準、P95 レイテンシ 200ms など）は定数化。
  - tools/__init__.py を追加（ツール群のパッケージ化）。

- リサーチ / ファクター計算（部分実装）
  - research/factor_research.py: DuckDB 接続を受け取り prices_daily / raw_financials を参照してモメンタム等のファクターを計算するモジュールを追加（モジュール冒頭と定数、関数 calc_momentum の雛形を含む。ファイルは途中まで実装）。

### Changed
- （初回リリースのため変更履歴はありません）

### Fixed
- （初回リリースのため修正履歴はありません）

### Security
- 機密情報 (.env) の取り扱いに関する注意書きを config_setup のドキュメントコメントに記載（.env を絶対に Git にコミットしない旨を明示）。

Notes / 備考
- 環境変数の自動ロードはプロジェクトルートの検出に依存するため、配布後やテスト環境で期待通りに動作しない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを抑制できます。
- Paper Trading と本番データは意図的に分離（PAPER_TRADING_SQLITE_PATH を使用）されており、run_execution は settings.is_paper フラグに基づいて適切な DB を選択します。
- 一部モジュール（execution.*、monitoring.* など）は起動スクリプトから組み立てる想定であり、外部実装（BrokerClient 実装や ExecutionEngine の詳細）が別ファイルに存在する前提です。

今後の予定（例）
- research/factor_research の完全実装（ファクター計算ロジックの完成）
- Strategy/Execution の細部実装および統合テスト
- DuckDB を使った分析パイプラインのドキュメント強化
- 単体テストと CI 設定の追加

---