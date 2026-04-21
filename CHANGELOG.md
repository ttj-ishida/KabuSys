CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。  
語尾は日本語。コードベースの内容から推測して記載しており、不明な実装詳細は要約しています。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更（破壊的変更あれば明記）
- Fixed: バグ修正
- Security: セキュリティに関する注意点

[Unreleased]
-------------

- なし

[0.1.0] - 2026-04-21
--------------------

Added
- 基本アーキテクチャ、コア機能を実装した最初の公開バージョン。
- 実行スクリプト
  - run_execution: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient（BrokerClientFactory 経由）を使用して paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）に記録するように分離。
    - 起動時にプロセス優先度を設定（utils.process_priority.set_process_priority を使用）。
    - 停止フラグ（data/stop_requested.flag）および実行 PID ファイル（data/execution.pid）をサポート。
  - run_monitoring: SystemMonitor のポーリングループを起動するエントリポイントを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書き（デフォルト 60 秒）。
    - 監視は環境に関係なく本番用 sqlite_path を使用する設計（監視データの一元化）。
    - 停止フラグの検知で安全にループを終了。
- 設定管理
  - config.Settings クラスを実装。環境変数から各種設定値（DB パス、API トークン、ログレベル、環境種別など）を取得するユーティリティを提供。
  - 自動 .env ロード機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
    - 読み込み優先順位: OS 環境 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用）。
  - .env パーサーは export 構文、クォート、インラインコメントなどに対応。
  - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、各種閾値（CPU/MEM/DISK）など専用プロパティを提供。
- 設定ユーティリティ CLI
  - config_setup: 対話式ウィザードで .env を初期作成・更新する CLI を追加（python -m kabusys.config_setup）。
    - シークレット入力、選択肢、デフォルト値の提示、保存確認などを実装。
    - .env を生成する際のテンプレートと注意書き（.env をコミットしない等）を出力。
  - validate_config: .env と config/*.yaml を起動前に検証する CLI を追加（python -m kabusys.validate_config）。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、ファイルパスの親ディレクトリ存在チェック、PyYAML があれば YAML のパース検証を実施。
    - --strict オプションで警告を失敗扱いにできる。
- ロギング/運用ユーティリティ
  - utils.logging_setup.setup_logging を追加。すべての起動スクリプトから共通で使用可能。
    - stdout への StreamHandler（標準出力）と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30 日保持）を設定。
    - LOG_DIR/LOG_LEVEL 環境変数や引数での上書きに対応。ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソールのみで継続。
  - utils.process_priority により OS (Windows / POSIX) を吸収したプロセス優先度設定を実装。
    - set_process_priority(level: "high"|"normal"|"low")、set_cpu_affinity(cpu_count) を提供。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder: 候補選定（select_candidates）、等重み（calc_equal_weights）、スコア加重（calc_score_weights）を実装。
    - スコアが全て 0 の場合は警告を出して等金額配分にフォールバック。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）を実装。
    - apply_sector_cap は既存保有のセクター別時価を計算してセクターブロックを適用（"unknown" セクターは除外しない）。
    - calc_regime_multiplier は "bull"/"neutral"/"bear" に対する乗数マップを提供（不明レジームは 1.0 にフォールバック）。
  - portfolio.position_sizing: 発注株数決定ロジックを実装（risk_based / equal / score）。
    - 単元株丸め（lot_size）、1 銘柄上限、aggregate cap、cost_buffer（手数料・スリッページの保守的見積り）を加味したスケーリング処理を実装。
    - スケーリング時には端数処理のため残差順に lot_size 単位で追加配分するアルゴリズムを採用。
- Execution 周辺コンポーネント（呼び出し元の組み立て）
  - BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine（EngineConfig）などを組み合わせて起動する設計を実装（run_execution が組み立てて使用）。
  - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）の例を示す実装あり。
- 監視データベース初期化
  - monitoring.monitoring_db.init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。
- 運用ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加（python -m kabusys.tools.paper_verification_report）。
    - 稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（avg/max/P95）などを集計して PASS/FAIL を判定する。
    - デフォルト DB パス: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。
- 研究モジュール（着手）
  - research.factor_research の骨子を追加。Momentum / MA / ATR 等の定義と calc_momentum の雛形（実装の途中）を配置。
- パッケージメタ
  - パッケージバージョンを __version__ = "0.1.0" に設定。

Changed
- 初期リリースのため、既存ライブラリからの大きな変更点はなし（新規実装中心）。

Fixed
- 初期リリースのため、既知のバグ修正履歴はなし。

Security
- .env ファイルに機密情報（J-Quants トークン、kabu API パスワード等）を保存する設計のため、README 等で .env をリポジトリにコミットしない旨を強く周知することを推奨。
- config_setup により .env を生成する際にも同様の注意書きを出力。

Notes / 運用上の注意
- 監視（run_monitoring）は監視用 sqlite_path（Settings.sqlite_path）を環境にかかわらず使用する設計になっているため、本番／ペーパーの分離ポリシーに注意すること。
- run_execution は KABUSYS_ENV=paper_trading 時に paper_trading 用 DB を使うが、設定ミスで本番 DB を使わないよう validate_config と .env の確認を必ず行うこと。
- MONITOR_POLL_INTERVAL 環境変数は正の整数を指定すること。無効値はデフォルト 60 秒へフォールバックする旨の警告が出る。
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存される（30 日保持）。ログディレクトリ作成に失敗した場合はコンソール出力のみで継続する。

今後の予定（推測）
- research.factor_research の完全実装（Momentum、Value、Volatility、Liquidity 等の出力整備）。
- ExecutionEngine / Broker のテスト補強、より詳細なエラーハンドリングと回復ロジック。
- 単元や銘柄別パラメータを許容するための拡張（lot_size の銘柄別指定など）。
- ドキュメント（運用手順、デプロイ方法、モニタリング/アラート設定）の整備。

----- 
（この CHANGELOG は提供されたコードの内容から推測して作成しています。実際のコミット履歴や意図と差分がある可能性があります。）