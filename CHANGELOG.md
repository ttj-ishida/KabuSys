# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
最新の変更は上に記載しています。

## [Unreleased]

### Added
- run_monitoring 起動スクリプトを追加
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 停止はプロジェクトの data/stop_requested.flag ファイルで制御。
  - Monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用して監視テーブルを初期化する。
  - duckdb を併用して分析用コネクションも確立する。

- run_execution 起動スクリプトを追加
  - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB（data/paper_trading.db）を使用し、本番 DB と分離。
  - 停止フラグ（data/stop_requested.flag）を検知して安全に停止。
  - 起動時に pid ファイルを書き込む（data/execution.pid）。ExecutionEngine をバックグラウンドスレッドで実行。

- 環境設定・検証コマンドを追加
  - config_setup.py: 対話式ウィザードで .env を生成・更新する CLI を追加。
  - validate_config.py: .env と config/*.yaml の検証 CLI を追加。--strict オプションで警告も失敗扱いにできる。

- 設定管理（kabusys.config）
  - .env 自動読み込み機能を追加（プロジェクトルート検出: .git または pyproject.toml）。
  - export 形式・クォート・インラインコメント等を考慮した .env パーサを実装。
  - Settings クラスを追加し、環境変数をプロパティ経由で安全に取得できるようにした（パス類は Path で返す）。
  - Paper Trading 用の PAPER_TRADING_SQLITE_PATH と PAPER_FILL_MODE（instant/partial/never/reject）を追加。
  - 監視閾値・pid/kill flag の設定プロパティを追加。

- ロギング・プロセスユーティリティを追加
  - utils.logging_setup: stdout 出力の StreamHandler と日次ローテーションの TimedRotatingFileHandler をルートロガーに統一的に設定。
    - LOG_DIR の自動作成に失敗した場合はファイルロギングをスキップして stdout のみで継続。
  - utils.process_priority: Windows / POSIX の差を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加。
    - CPU affinity を設定する set_cpu_affinity 関数も提供。
  - 起動スクリプト（monitoring / execution）は起動直後にプロセス優先度を "high" に設定するように変更。

- ポートフォリオ構築モジュールを追加（kabusys.portfolio）
  - portfolio_builder: シグナル選定（select_candidates）と配分重み（calc_equal_weights, calc_score_weights）を実装。スコアが全て 0 の場合は等配分にフォールバック。
  - risk_adjustment: セクター集中度チェック（apply_sector_cap）と市場レジームに基づく投下資金乗数（calc_regime_multiplier）を実装。unknown セクターは上限チェックを適用しない。
  - position_sizing: allocation_method（risk_based / equal / score）に基づく発注株数計算を実装。lot_size（単元株）で丸め、aggregate cap（利用可能現金超過時）のスケーリング処理や cost_buffer（手数料・スリッページ見積り）を考慮。

- 分析・レポートツールを追加
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、レイテンシ（平均 / 最大 / P95）等を集計し PASS/FAIL 判定を出力。
    - 日付フィルタ（--from / --to）と DB パス指定（--db / 環境変数）に対応。
    - DB ファイルやテーブルが存在しない場合でも例外を吸収して N/A 表示などで優雅に処理。

- 研究用ファクター計算（research）
  - factor_research モジュール（モメンタム等のファクター計算）を追加（DuckDB を利用した設計）。（実装途中での導入）

### Changed
- .env 自動読み込みの優先順位を明確化: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能。
- logging_setup: ファイル出力に失敗した場合の挙動を明確化（警告出力し、コンソール出力のみで継続）。
- logging_setup: StreamHandler は stdout を使用（stderr ではなく）、タスクスケジューラ等からのリダイレクトを想定。

### Fixed
- .env パーサの強化により、export 前置、クォート内のバックスラッシュエスケープ、インラインコメントなどのパターンに対応。

---

## [0.1.0] - 2026-04-20

初回リリース — 基本機能の実装。

### Added
- コアパッケージ初期実装
  - __init__.py にバージョン定義（0.1.0）を追加。

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動する基本フローを実装。BrokerClientFactory によるブローカ抽象化、OrderRepository / OrderManager / RiskManager / Reconciler の組立て、ExecutionEngine の起動と停止制御を実装。
  - run_monitoring.py: SystemMonitor を定期実行するポーリングループを実装。DB 初期化と監視チェックを実行。

- 設定管理
  - config.py: Settings クラスを実装し、各種環境変数を安全に取得・検証するプロパティを提供。
  - 環境変数未設定時のエラーや不正値の早期検出を実装。

- 設定支援ツール
  - config_setup.py: 対話式 .env ウィザードを実装（J-Quants トークンや KABU API パスワード等の入力を支援）。
  - validate_config.py: 設定検証 CLI を実装（必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL チェック、DB パスの親ディレクトリチェック、config/*.yaml の存在・パース検証、live 環境向けの注意喚起）。

- ロギング
  - utils/logging_setup.py: 共通ロギング設定ユーティリティを実装（stdout と日次ローテーションファイル）。

- プロセス制御
  - utils/process_priority.py: プロセス優先度（nice/HIGH_PRIORITY_CLASS）設定と CPU affinity 設定ユーティリティを追加。

- ポートフォリオ構築（基本）
  - portfolio モジュール（選定・重み付け・リスク調整・株数計算）を実装。
    - 等配分・スコア配分、セクターキャップ、レジーム乗数、risk-based sizing 等をサポート。

- 分析用 DB（DuckDB）統合
  - 起動スクリプトや research モジュールで duckdb 接続を確立する設計を採用。

- Paper Trading の分離
  - Paper Trading 用に専用 SQLite パス（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を用意し、本番 DB と運用を分離。

### Changed
- 起動スクリプトとコンポーネントはログ出力と例外捕捉を強化（予期せぬ例外発生時はログに残してループ継続等）。

### Fixed
- 監視・実行プロセス停止制御に関する基本的な同期問題を調整（stop flag の検知ロジック等）。

---

注記:
- 上記はコードベースの内容から復元した推測ベースの変更履歴です。実際のコミット履歴やタグとは差異がある可能性があります。必要であれば特定ファイル・機能ごとにより細かい変更箇所に分割して反映できます。