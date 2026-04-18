# Changelog

すべての重大な変更点を記載します。本ファイルは「Keep a Changelog」形式に準拠しています。

通常の利用者向けにはリリースごとのセクションを参照してください。

- すべての変更は semver に従って管理します（現状は初期リリース）。
- 日付はパッケージ内の __version__ に合わせて設定しています。

## [Unreleased]
（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-18

### Added
- 初期公開リリース。
- 実行スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、SQLite / DuckDB 接続、Broker クライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、デーモン実行と停止フラグ監視を実装。
    - paper_trading 環境時は専用の paper_sqlite_path（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全に分離して動作。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）に対応。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV に依存せず本番用 sqlite_path を使用する（監視データは常に本番 DB）。
    - 停止フラグ検出によるループ終了、KeyboardInterrupt による終了処理を実装。
- 設定管理
  - config.Settings: 環境変数から各種設定値を取得するクラスを追加（DB パス、API トークン、ペーパートレード設定、監視しきい値など）。
  - 自動 .env ロード: プロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を自動読み込み（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パーサー: export KEY=val 形式、クォート文字列、エスケープシーケンス、インラインコメント処理に対応する堅牢なパーサーを実装。
- 設定ユーティリティ
  - config_setup: 対話式 .env 作成ウィザードを追加（python -m kabusys.config_setup）。
    - 主要な設定項目の対話入力、既存 .env 読込、保存機能を提供。
  - validate_config: 起動前検証 CLI を追加（python -m kabusys.validate_config）。
    - 必須環境変数、KABUSYS_ENV、LOG_LEVEL、DB パス、config/*.yaml の存在と YAML パース（PyYAML が無い場合は警告）などをチェック。
    - --strict フラグで警告を FAIL 扱いにできる。
- ポートフォリオ構築モジュール（純粋関数）
  - portfolio_builder: 候補選定 select_candidates、等配分 calc_equal_weights、スコア加重 calc_score_weights（スコア全0時に等配分へフォールバック）を実装。
  - risk_adjustment: セクター集中制限 apply_sector_cap（当日売却予定の銘柄を除外できる）、市場レジーム乗数 calc_regime_multiplier（bull/neutral/bear をマップ、未知レジームはフォールバック）を実装。
  - position_sizing: 株数計算 calc_position_sizes を実装。allocation_method（risk_based / equal / score）、単元（lot_size）丸め、per-position 上限、aggregate cap（利用可能現金へのスケーリング）、cost_buffer（手数料/スリッページ見積り）による保守的見積り、余剰配分ロジック等を実装。
- ユーティリティ
  - utils.logging_setup: 統一ログ設定ユーティリティを追加。stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）を設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
  - utils.process_priority: psutil を用いたクロスプラットフォームなプロセス優先度設定（high/normal/low）と CPU affinity 設定ユーティリティを追加。Windows / POSIX の差分を吸収し、権限不足や未対応プラットフォームでは警告を出して安全にスキップする。
- 分析・検証ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加（python -m kabusys.tools.paper_verification_report）。
    - system_status / trade_logs / risk_logs を参照して稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等を集計し、基準値と比較して PASS/FAIL を出力。
    - デフォルト閾値: 稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms。
- リサーチ基盤（部分実装）
  - research.factor_research: DuckDB 接続を受けてモメンタム等のファクターを計算する基礎を追加（関数 calc_momentum 等、設計方針と定数群を含む）。（注: ソースは一部で途切れており、今後の完成が予定されています）

### Changed
- ログ挙動
  - ログは標準エラーではなく標準出力（stdout）へ出力するようにデフォルト設計。cron やスケジューラでの stdout/stderr 統合を想定。
- DB 初期化
  - 起動時に init_monitoring_db() を呼ぶことで監視用テーブルが存在することを冪等に保証（存在しない場合は作成）。
- Execution/run の挙動
  - run_execution は paper_trading 環境時にペーパートレード専用 DB を使うことで、本番 DB と明確に分離。paper_trading 環境では MockBrokerClient を利用する設計（BrokerClientFactory が環境に応じて生成）。

### Fixed
- 環境変数読み込みの堅牢化
  - .env のパースでクォート内のエスケープや inline comment の扱い、export プレフィックスに対応。誤った行をスキップして安全に読み込むよう改良。
- MONITOR_POLL_INTERVAL の不正値処理
  - MONITOR_POLL_INTERVAL が整数変換できない、または 0 以下の場合は警告を出してデフォルト（60 秒）にフォールバックし、time.sleep による ValueError を回避。
- プロセス優先度・CPU affinity 設定での失敗安全化
  - 権限不足や未対応プラットフォームで例外が発生しても警告を出して処理を継続するように修正。

### Security
- .env ファイルの取り扱いに関する注意書きを config_setup に追加（.env を Git にコミットしないことを明記）。

### Notes / Breaking changes
- 監視（run_monitoring）は KABUSYS_ENV に関係なく監視用 DB として Settings.sqlite_path を使用します。KABUSYS_ENV が paper_trading の場合でも監視データは本番用 sqlite_path を参照する設計になっているため、運用時は監視 DB パスの設定に注意してください（監視データと発注データを分離したい場合は sqlite_path を適切に設定してください）。
- Settings.env の値が無効な場合は ValueError を送出するため、環境変数 KABUSYS_ENV を事前に確認してください（validate_config で検出可能）。

---

開発／運用上の補足:
- CLI:
  - 環境設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- パッケージバージョン: __version__ = "0.1.0"

今後の予定:
- research.factor_research の完成（ファクター計算の実装完了、DuckDB SQL の最適化）
- 実運用での監視・アラート（LINE）連携強化
- 銘柄ごとの lot_size 管理、手数料/スリッページの詳細モデル化
- テストカバレッジと CI の強化

-----------------------------------------------------------------------------
記載内容はソースコードの実装から推測してまとめたものです。実際のリリースノート作成時にはコミットログ・変更差分を参照のうえ微調整してください。