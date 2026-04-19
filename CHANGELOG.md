# CHANGELOG

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠しています（英語ではなく日本語で記載しています）。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正・堅牢性向上
- Deprecated / Removed / Security: 該当なしの場合は省略

## [Unreleased]

### Added
- 環境および起動関連のユーティリティ／CLIを追加・改善
  - config_setup: 対話式ウィザードで .env ファイルを生成・更新する CLI を追加（.env のテンプレート化、シークレットのマスク表示、既存値の再利用など）。
  - validate_config: .env と config/*.yaml を起動前に検証する CLI を追加（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス確認、YAML の存在とパース検証、`--strict` オプション）。
  - run_execution/run_monitoring: 実行エンジンと監視ループの起動スクリプトを追加（PID/stop フラグによる制御、プロセス優先度設定、DuckDB/SQLite 接続、ログ設定の統一呼び出し）。

- 環境変数読み込み機構の強化
  - プロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を自動ロードする機能を追加。
  - .env ファイルパーサを強化：export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント取り扱いをサポート。
  - OS 環境変数を保護するための上書き制御（protected set）を導入。

- 設定オブジェクト（Settings）を追加
  - J-Quants、kabu API、LINE、データベースパス、監視閾値、各種フラグ等を環境変数から取得するプロパティを提供。
  - KABUSYS_ENV / LOG_LEVEL 等の値検証を実施し、不正値は例外で通知。
  - Paper Trading 関連: PAPER_FILL_MODE の妥当性検査、paper_sqlite_path の分離サポート。

- ロギング／プロセス管理ユーティリティを追加
  - utils.logging_setup: stdout への StreamHandler と日次ローテーションする TimedRotatingFileHandler をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils.process_priority: Windows/Linux/macOS でプロセス優先度（nice / HIGH_PRIORITY_CLASS）を設定するユーティリティを追加。CPU affinity を設定する set_cpu_affinity も実装。権限不足時には警告を出して安全にスキップ。

- Execution / Monitoring のランタイム機能
  - run_execution:
    - Paper Trading 環境では MockBrokerClient を利用し、本番 DB と分離した paper_trading DB を使用。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler/ExecutionEngine の組み立てを実装。
    - RiskManager のデフォルト RiskConfig を定義（max_position_pct 等）し、initial_portfolio_value をブローカー残高から初期化。
    - エンジンはスレッドでデーモン実行し、data/stop_requested.flag による停止をサポート。PID ファイルの使用。
  - run_monitoring:
    - SystemMonitor の初期化とポーリングループを実装。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視データは本番 DB に記録）。

- ポートフォリオ構築・リスク管理モジュールを追加
  - portfolio.portfolio_builder:
    - シグナルソート（score 降順／signal_rank タイブレーク）、候補選定、等金額・スコア重み付けを実装。スコア合計が 0 の場合のフォールバック警告。
  - portfolio.risk_adjustment:
    - セクター集中制限適用（apply_sector_cap）、既存ポジションと当日売却予定を考慮したフィルタリング。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear、およびフォールバック）を実装。
  - portfolio.position_sizing:
    - リスクベース／等配分／スコア配分に対応した株数計算 calc_position_sizes を実装。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash）に基づくスケーリング、端数配分アルゴリズムを導入。

- 解析・ツール
  - tools.paper_verification_report:
    - Paper Trading 用の検証レポート生成スクリプトを実装（稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）等を集計）。
    - 基準値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）で PASS/FAIL を判定。
    - P95 の計算ユーティリティを実装し、日付フィルタ（ISO8601）に対応。
  - research.factor_research:
    - DuckDB を用いたファクター計算モジュールを追加（Momentum、Value、Volatility、Liquidity を想定）。calc_momentum 等の関数を実装開始（注: 一部実装が途中で切れているファイルあり）。

### Changed
- ログ出力の一貫化
  - すべての起動スクリプトから utils.logging_setup.setup_logging を呼び出すことでログ設定を統一。ログレベル・ログディレクトリは環境変数で上書き可能。
  - StreamHandler は stdout を使用（cron/Task Scheduler の出力リダイレクトを想定）。

- DB の取り扱い
  - run_monitoring は環境に関係なく本番用 sqlite_path を使うように仕様を明確化（監視データは本番 DB に記録する方針）。
  - run_execution は paper_trading の場合に専用の paper_sqlite_path を使って本番 DB と分離。

### Fixed / Robustness
- .env パーサの堅牢化により、引用符・エスケープ・コメントなどの特殊ケースを正しく取り扱うように改善。
- validate_config:
  - PyYAML 未インストール時に YAML 内容検証をスキップして警告を出すようにし、依存ライブラリが無くても実行できるよう改善。
  - config/*.yaml の存在チェックとパースエラーハンドリングを強化。
- logging_setup:
  - ログディレクトリ作成失敗やファイルハンドラ生成失敗時に、コンソール出力のみで安全に継続するフォールバックを実装。
- process_priority / set_cpu_affinity:
  - サポートされない OS、権限不足、psutil 未対応機能に対して安全に処理をスキップして警告を出すように修正。
- run_execution / run_monitoring:
  - stop フラグや KeyboardInterrupt に対して安全にクリーンアップ（DB 接続クローズ、engine.stop 呼び出し）を行うように改善。
- portfolio.position_sizing:
  - aggregate cap 適用時のスケーリングと端数配分において、単元（lot_size）丸めや上限チェックを厳格化し、再現性を確保するための安定ソートを導入。

---

## [0.1.0] - Initial release
リポジトリの初期リリース。上記の主要機能をまとめて追加。

### Added
- プロジェクトのコア機能を多数追加:
  - 環境設定管理（Settings）、.env 自動ロード、対話式ウィザード（config_setup）、設定検証ツール（validate_config）。
  - 実行系: run_execution（ExecutionEngine の起動/停止制御、RiskManager/OrderManager 等の組み立て）、run_monitoring（SystemMonitor ポーリングループ）。
  - ロギング、プロセス優先度・CPU affinity ユーティリティ（psutil を利用）。
  - ポートフォリオ構築（銘柄選定、重み計算、ポジションサイズ計算、セクターキャップ、レジーム乗数）。
  - Paper Trading 向け検証ツール（paper_verification_report）。
  - DuckDB 連携による分析・ファクター計算の骨組み（research.factor_research）。
  - パッケージメタ情報（__version__ = "0.1.0"）。

### Changed
- 初期設計時点の挙動・構成を規定（上記の「Changed」欄参照）。

### Fixed
- 初期実装の堅牢性確保（上記の「Fixed / Robustness」欄参照）。

---

注意:
- research.factor_research の一部関数は実装が途中で切れています（ファイル末尾が不完全）。本格利用前に実装の完了およびテストを推奨します。
- 本 CHANGELOG はソースコード内容から推測して作成しています。実際のコミット履歴・リリースノートと差異がある場合があります。必要に応じて適宜編集してください。