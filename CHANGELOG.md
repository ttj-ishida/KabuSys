# Changelog

すべての変更は Keep a Changelog の形式に従います。  
慣例: バージョン番号は semver に準拠します。日付はリリース日です。

## [0.1.0] - 2026-04-23

### Added
- 初期公開: KabuSys 自動売買フレームワークの基盤機能を追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。
- 起動スクリプト / 実行環境
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視モードは環境にかかわらず本番用 `sqlite_path` を使用する設計。
    - 停止フラグ（data/stop_requested.flag）を検知して安全にループを終了。
    - プロセス優先度を "high" に設定して実行。
    - SQLite / DuckDB 接続の初期化を行い、例外発生時もログ出力してループ継続。
  - run_execution: ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - `KABUSYS_ENV=paper_trading` の場合は MockBroker を利用し、paper_trading 専用 DB（data/paper_trading.db）を使用して本番 DB から分離。
    - 停止フラグ/実行 PID ファイルの取り扱い（data/stop_requested.flag, data/execution.pid）。
    - コンポーネント組み立て（BrokerFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）を行いスレッドで実行。
    - プロセス優先度を "high" に設定。

- 設定管理
  - Settings クラスを追加し環境変数をラップ（src/kabusys/config.py）。
    - DB パス、ログレベル、KABUSYS_ENV、paper_trading 用設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等）を提供。
    - `.env` 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env 読み込みは OS 環境変数を保護しつつ `.env` / `.env.local` を適切な優先度でロード。自動読み込みを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` に対応。
    - 環境変数の必須チェック用ヘルパ `_require` を提供。

- 設定支援 / 検証ツール
  - config_setup: 対話式の .env 作成ウィザードを追加（src/kabusys/config_setup.py）。
    - シークレットマスク、選択肢提示、既存 .env の読み込み、保存機能を実装。
  - validate_config: 起動前に .env / config/*.yaml の妥当性を検証する CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリ存在確認、YAML のパース検証（PyYAML があれば実施）、本番環境用の追加警告等。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - logging_setup: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次）を設定するユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - ログディレクトリ作成失敗時はファイル出力を無効化してコンソール出力のみで継続。
    - LOG_LEVEL / LOG_DIR に基づく設定と既存ハンドラの適切なクリーンアップを実装。
  - process_priority: Windows / POSIX の差分を吸収してプロセス優先度や CPU affinity を設定するユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows 用優先度マップ、POSIX 用 nice 値、CPU affinity 設定関数を提供。
    - アクセス権限や未対応 OS の場合は警告ログを出力してフォールバック。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder（src/kabusys/portfolio/portfolio_builder.py）
    - 候補選定 select_candidates、等分配 calc_equal_weights、スコア加重 calc_score_weights を実装。
    - スコア合計が 0 の場合は等分配にフォールバックして警告。
  - risk_adjustment（src/kabusys/portfolio/risk_adjustment.py）
    - セクター集中上限を適用する apply_sector_cap を実装（売却予定銘柄除外、unknown セクターの扱い等）。
    - 市場レジームに応じた乗数 calc_regime_multiplier を実装（bull/neutral/bear とフォールバック挙動）。
  - position_sizing（src/kabusys/portfolio/position_sizing.py）
    - allocation_method（risk_based / equal / score）に基づく発注株数計算を実装。
    - lot_size（単元）丸め、1銘柄上限、aggregate cap（available_cash を超えた際のスケーリングと残差配分）を実装。
    - cost_buffer（スリッページ/手数料見積り）を考慮した保守的見積りをサポート。

- 分析 / レポート
  - tools.paper_verification_report（src/kabusys/tools/paper_verification_report.py）
    - ペーパートレード用 SQLite DB から以下指標を集計してレポート出力: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、リスク却下数、API レイテンシ（avg/max/P95）など。
    - P95 計算、期間フィルタ機能、閾値に基づく PASS/FAIL 判定を実装。
    - DB が存在しない場合のエラーとパス解決（--db / 環境変数 / デフォルト）をサポート。

- 研究モジュール（下地）
  - research.factor_research（src/kabusys/research/factor_research.py）
    - モメンタム等のファクター計算の設計骨子と定数を追加（DuckDB 接続を受け取り prices_daily / raw_financials を参照する想定）。実装は途中（モジュール冒頭〜関数シグネチャまで含む）。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Known issues / Notes
- research.factor_research の実装は途中で終了している箇所があり（ファイル末尾で処理が中断）、今後の実装/テストが必要。
- position_sizing の一部（価格欠損時のフォールバック挙動）は TODO コメントあり。前日終値や取得原価でのフォールバックを将来的に検討する旨を注記。
- .env 自動ロードはプロジェクトルートが自動検出できない場合はスキップされるため、配布後やパッケージ化後の挙動に注意。

---

今後の予定（例）
- factor_research の完全実装と単体テスト追加
- ExecutionEngine / SystemMonitor の統合テスト、自動化された CI ワークフロー
- 個別ユーティリティのユニットテスト整備（process_priority, logging_setup 等）

（この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴や意図に基づく細かい差分はプロジェクトの VCS 履歴を参照してください。）