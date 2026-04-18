CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。
semantic versioning を意識した記述を行っています。

[Unreleased]
------------

- なし

0.1.0 - 2026-04-18
------------------

Added
- 初回公開: KabuSys 0.1.0 をリリース。
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）と本番 DB を分離して動作する。
  - run_monitoring.py: SystemMonitor 起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する設計。
- 設定管理
  - config.py: Settings クラスを導入。環境変数・.env/.env.local の自動読み込み（プロジェクトルート検出による）に対応。多くの設定プロパティ（DB パス、PID/kill flag、閾値、PAPER_FILL_MODE 等）と入力検証ロジックを実装。
  - config_setup.py: 対話式 .env ウィザードを追加（python -m kabusys.config_setup）。既存 .env の読み込み・マスク表示・バリデーションあり。保存時のテンプレート出力をサポート。
  - validate_config.py: 起動前の設定検証 CLI を追加（python -m kabusys.validate_config）。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在と YAML パース（PyYAML がある場合）などをチェック。--strict オプションで警告も失敗扱いにできる。
- 監視/運用ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成ツールを追加（python -m kabusys.tools.paper_verification_report）。稼働率、注文成功率、送信率、レイテンシ（P95 など）、リスク却下数を集計し PASS/FAIL 判定を出力。日付フィルタ/DB 指定オプションあり。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。スコア全0 の場合のフォールバック警告を実装。
  - portfolio/risk_adjustment.py: セクター集中制限 (apply_sector_cap) とレジーム乗数 (calc_regime_multiplier) を実装。未知レジームはフォールバック（1.0）し、警告出力あり。
  - portfolio/position_sizing.py: ポジションサイズ計算機能を追加。allocation_method に "risk_based" / "equal" / "score" をサポート。単元株丸め（lot_size）、max_position_pct、max_utilization、cost_buffer（手数料/スリッページ見積り）を考慮した aggregate cap のスケーリングロジックを実装。価格欠損時のスキップやデバッグログを出力。
  - portfolio/__init__.py で上記 API をエクスポート。
- ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。コンソール出力は stdout、日次ローテーションファイルハンドラ（TimedRotatingFileHandler）を設定。LOG_LEVEL / LOG_DIR / app_name による設定、ログディレクトリ作成失敗時のフォールバック処理を実装。
  - utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加。Windows と POSIX (Linux, macOS, FreeBSD) の差異を吸収し、psutil を利用して優先度設定・CPU ピンニングを行う。権限不足等で失敗した場合は警告でスキップ。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Notes / Implementation details
- .env 自動ロードはデフォルトで有効。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可能。
- .env パーサ (_parse_env_line) は export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント等を考慮する堅牢な実装。
- Settings のプロパティでは入力検証（例: KABUSYS_ENV の許容値、LOG_LEVEL の許容値、PAPER_FILL_MODE の有効値チェック）を行い、早期に誤設定を検出できる。
- run_execution は起動前に監視テーブルの存在を保証する（init_monitoring_db を呼ぶ）ため、監視用テーブルがない環境でも安全に起動できるよう配慮している。
- run_monitoring / run_execution ともにプロセス優先度を最初に "high" に設定する設計。停止はプロジェクト内 data/stop_requested.flag を検知して行う。
- paper_verification_report はデフォルトの閾値を内部定数として持ち、P95 は簡易実装でパーセンタイル近似に ceil を用いる。
- research/factor_research.py や一部ドキュメント参照（PortfolioConstruction.md, StrategyModel.md 等）は分析・戦略実装の設計方針や計算対象を示す初期実装を含む（ファクター計算ロジックの実装を順次拡充予定）。

Security
- 機密情報（J-Quants トークン、kabu API パスワード）を .env に保存することを想定。config_setup のヘルプや .env テンプレートで .env を Git にコミットしないことを強調。

Appendix
- パッケージバージョンは src/kabusys/__init__.py の __version__ = "0.1.0" に合わせています。