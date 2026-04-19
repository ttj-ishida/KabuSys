# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

### Added
- 起動スクリプトを追加 / 強化
  - 監視用ポーリングループ起動スクリプト run_monitoring.py を追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグ（data/stop_requested.flag）検知で安全に終了する実装（src/kabusys/run_monitoring.py）。
  - 実行エンジン起動スクリプト run_execution.py を追加。スレッドで ExecutionEngine を実行し、停止フラグ/PID 管理をサポート（src/kabusys/run_execution.py）。

- 設定管理・セットアップ・検証ツールを追加
  - Settings クラスにより環境変数からアプリ設定を一元取得（src/kabusys/config.py）。
  - 自動 .env ロード機能を追加（プロジェクトルート検出: .git / pyproject.toml）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化も可能（src/kabusys/config.py）。
  - 環境設定ウィザード CLI を追加（python -m kabusys.config_setup）。対話的に .env を作成・更新可能（src/kabusys/config_setup.py）。
  - 設定検証 CLI を追加（python -m kabusys.validate_config）。必須環境変数や config/*.yaml、パスの検証、production 向けのガードチェック等を実行（src/kabusys/validate_config.py）。

- Paper Trading / 分離された DB サポート
  - Paper Trading 用に専用 SQLite パスをサポート（PAPER_TRADING_SQLITE_PATH / Settings.paper_sqlite_path）。paper_trading 環境では MockBroker を用いた DB 分離が行われる（src/kabusys/run_execution.py, src/kabusys/config.py）。
  - PAPER_FILL_MODE（instant/partial/never/reject）でペーパートレードの約定挙動を設定可能（src/kabusys/config.py）。

- ロギング・プロセス制御ユーティリティを追加
  - 統一的なロギング初期化ユーティリティ setup_logging を追加。コンソール(stdout) と 日次ローテートファイル出力を設定。ログディレクトリ作成失敗時はファイル出力をスキップして継続（src/kabusys/utils/logging_setup.py）。
  - プロセス優先度・CPU affinity 設定ユーティリティを追加。Windows/Linux/macOS の違いを吸収しつつ優先度設定や affinity 固定をサポート（src/kabusys/utils/process_priority.py）。

- ポートフォリオ構築・リスク調整・ポジションサイズ算出機能を追加
  - 銘柄選定・重み計算モジュール（select_candidates, calc_equal_weights, calc_score_weights）（src/kabusys/portfolio/portfolio_builder.py）。
  - セクター集中制限・レジーム乗数（apply_sector_cap, calc_regime_multiplier）（src/kabusys/portfolio/risk_adjustment.py）。
  - 発注株数計算（allocation: risk_based / equal / score）、単元丸め、aggregate cap スケーリング、cost_buffer を考慮した position sizing（src/kabusys/portfolio/position_sizing.py）。

- 分析・検証ツール
  - Paper Trading 検証レポート生成スクリプトを追加。稼働率 / 注文成功率 / 送信率 / API レイテンシ (P95) 等を計算して PASS/FAIL 判定を出力（src/kabusys/tools/paper_verification_report.py）。
  - DuckDB を使ったリサーチ用のファクター計算モジュール（ファイルの途中まで実装、モメンタム等の因子計算を想定）（src/kabusys/research/factor_research.py）。

### Changed
- DB 周り動作の明確化
  - 監視（monitoring）関連は環境に関係なく本番用 sqlite_path を使用する旨を明確化（src/kabusys/run_monitoring.py）。
  - run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使用して本番 DB と完全に分離して動作（src/kabusys/run_execution.py）。
  - 監視用 DB の初期化関数 init_monitoring_db を起動時に呼び、監視テーブルの存在を冪等に保証（src/kabusys/run_monitoring.py / src/kabusys/run_execution.py）。

- ログ設定の挙動調整
  - 既存ハンドラが設定されている場合は一旦 flush/close してから再設定することで二重出力を防止（src/kabusys/utils/logging_setup.py）。
  - コンソール出力は stdout を優先（cron/task 実行時のリダイレクト考慮）（src/kabusys/utils/logging_setup.py）。

### Fixed
- 環境値の堅牢なパース
  - .env ファイルの解析を強化（export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメント処理、空行・コメント行の無視等）（src/kabusys/config.py）。
  - MONITOR_POLL_INTERVAL 等の無効値が設定された場合にデフォルトへフォールバックする警告処理を追加（src/kabusys/run_monitoring.py）。
  - process priority / cpu affinity 設定時の権限エラーや未実装 API に対する例外を捕捉して警告に変換（src/kabusys/utils/process_priority.py）。

### Security
- 環境変数の取り扱い
  - .env に含めるべき機密情報はウィザードでマスク表示（secret フラグ）や README へ明記（src/kabusys/config_setup.py）。
  - .env の自動ロードはデフォルトで有効だが、明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）（src/kabusys/config.py）。

### Notes / Internal
- パッケージバージョンを __version__ = "0.1.0" に設定（src/kabusys/__init__.py）。
- 多数の TODO / 将来的な拡張注記をコード内に記載（例: position_sizing の銘柄別 lot_size 拡張、apply_sector_cap の価格フォールバック等）。

---

## [0.1.0] - 2026-04-19

初回リリース相当の状態を記録します（リポジトリ内に示された現行実装を元に推測）。

### Added
- 基本的なアプリケーション構成と CLI
  - 実行・監視の起動スクリプト（run_execution.py / run_monitoring.py）。
  - 環境設定ウィザード（config_setup.py）と設定検証ツール（validate_config.py）。
- データ基盤・バックエンド
  - DuckDB / SQLite を利用するデータ接続基盤の導入。
  - 監視テーブルの初期化ユーティリティ（init_monitoring_db を想定）。
- コア機能
  - ExecutionEngine 周辺の骨格（broker factory, order manager, reconciler, risk manager, execution engine の組み立て）。
  - Portfolio construction（選定・重み付け・リスク調整・ポジションサイズ算出）。
  - Paper Trading 用のモックブローカーサポートと専用 DB 分離。
- ユーティリティ
  - ロギングセットアップ、プロセス優先度設定ユーティリティ。
  - Paper Trading 検証レポートツール。
  - DuckDB ベースのファクター計算（factor_research の実装開始）。

### Changed
- 初期設計に応じた環境変数命名・検証ルールを導入（KABUSYS_ENV の検証、ログレベルなど）。
- .env 自動ロード機能を追加（プロジェクトルート検出）。

### Fixed
- 起動時の一般的な堅牢性向上（ログディレクトリ作成失敗時のフォールバック、例外キャッチによる監視ループ継続等）。

---

注記:
- 上記はソースコードから推測して作成した変更履歴です。実際のコミット履歴・差分がある場合はコミットメッセージに基づき正式な CHANGELOG を作成することを推奨します。必要であればコミット差分や時系列（リリース日付）を反映した修正版を作成します。