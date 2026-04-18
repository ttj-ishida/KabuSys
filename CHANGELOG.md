# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  
リンクや参照はリポジトリ運用に合わせて適宜追加してください。

最新更新日: 2026-04-18

## [Unreleased]

### Added
- 実行・監視用の起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動する CLI スクリプト。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）に記録する。停止フラグ（data/stop_requested.flag）や PID ファイル管理（data/execution.pid）に対応。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番 sqlite_path を参照する点を明示。
- 設定管理・検証・セットアップ用ツールを追加
  - config.py: .env の自動ロード（.env, .env.local）、export プレフィックス・クォート対応のパーサ、環境変数取得ユーティリティ（Settings クラス）を実装。
  - config_setup.py: 対話式ウィザードで .env を初期作成 / 更新する CLI を実装。
  - validate_config.py: .env と config/*.yaml の事前検証 CLI を追加。--strict オプションで警告を失敗扱いにできる。PyYAML がない場合は YAML 検証をスキップして警告を出す。
- ロギング・プロセス管理ユーティリティを追加
  - utils/logging_setup.py: stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler をルートロガーに設定する共通ユーティリティ。LOG_DIR 環境変数や引数でログ出力先を指定可能。
  - utils/process_priority.py: Windows/Linux/macOS の差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティと、CPU affinity を設定する関数を追加。権限不足時は警告を出してフォールバック。
- ポートフォリオ構築関連の純粋関数群を追加（DB 参照なし）
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights)。
  - portfolio/risk_adjustment.py: セクター集中上限適用 (apply_sector_cap)、レジームに応じた投下資金乗数 (calc_regime_multiplier)。
  - portfolio/position_sizing.py: 株数決定ロジック（risk_based / equal / score）、単元株丸め、aggregate cap によるスケールダウンロジックを実装。
- 分析・検証ツールを追加
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプト。稼働率・注文成功率・送信率・レイテンシ（P95）などを集計し PASS/FAIL を判定する。PAPER_TRADING_SQLITE_PATH 環境変数／--db で DB を指定可能。
- 研究用ファクター計算モジュールを追加（未完）
  - research/factor_research.py: DuckDB の prices_daily/raw_financials を利用して Momentum / Value / Volatility / Liquidity ファクターを計算する設計骨格を追加（モジュール構成・定数・関数宣言を含むが一部未完）。

### Changed
- 各起動スクリプトで起動直後に set_process_priority("high") を呼び出すようにして、重要プロセスの実行優先度を上げる挙動に統一。
- ExecutionEngine の起動フローを整理。依存コンポーネント（Broker, OrderRepository, OrderManager, RiskManager, Reconciler）を明示的に組み立て、スレッドで run_session を実行。停止フラグ検知時は engine.stop() を呼び出して安全停止を試みる。

### Fixed
- monitoring の初期化を idempotent に（init_monitoring_db を起動時に呼び出し、テーブル存在を保証）。
- .env パーサの堅牢化: export プレフィックス対応、シングル/ダブルクォート中のエスケープ処理、インラインコメント処理を改善。

### Security
- .env を生成する際のテンプレートコメントに「.env は絶対に Git にコミットしないこと」を明記。

---

## [0.1.0] - 2026-04-18

初回リリース

### Added
- 基本的な自動売買プラットフォームのコア機能を追加
  - 実行（ExecutionEngine）と監視（SystemMonitor）を起動するスクリプト群
  - 環境設定管理（Settings）と .env 自動ロード機能
  - 対話式 .env ウィザード（config_setup）と設定検証ツール（validate_config）
  - ログ設定ユーティリティ（stdout + 日次ローテーション）
  - プロセス優先度設定ユーティリティ（クロスプラットフォーム対応）
  - ポートフォリオ構築用純粋関数群（候補選定・重み付け・ポジション決定・セクター制限・レジーム乗数）
  - Paper Trading 向け検証レポート生成ツール
  - 研究用ファクター計算モジュール（骨格）
- 設定例・テンプレートの埋め込みと CLI ヘルプを整備

### Changed
- デフォルト設定:
  - 監視ポーリング間隔: 60 秒（MONITOR_POLL_INTERVAL で上書き可能）
  - DuckDB / SQLite のデフォルトパス: data/kabusys.duckdb / data/monitoring.db
  - Paper Trading のデフォルト SQLite: data/paper_trading.db
  - ログのデフォルトディレクトリ: logs/
- Execution と Monitoring の DB 接続: DuckDB を分析用に併用、SQLite を状態保存に利用

### Fixed
- 起動時の一部初期化シーケンスと例外ハンドリングを改善（監視ループ内での例外はログ出力して継続）

---

注意事項 / 既知の制限
- research/factor_research.py は実装途中の箇所が含まれます。ファクター計算の全機能は未完成です。
- process_priority の設定は実行環境の権限に依存します。権限不足時は警告ログを出して処理をスキップします。
- .env 自動ロード機能はプロジェクトルートの検出に .git または pyproject.toml を利用します。配布パッケージ等でプロジェクトルートが検出できない場合は自動ロードがスキップされます。
- Paper Trading と Live の DB は明示的に分離されていますが、運用時は環境変数を適切に設定してください。

--- 

変更履歴の補足（作成にあたっての推測）
- 本 CHANGELOG は提供されたソースコードの内容とコメントから推測して作成しています。実際のリリースノートやコミット履歴と差異がある可能性があります。実際のリリース運用では Git のコミットログやリリースタグに基づく正式な CHANGELOG を作成してください。