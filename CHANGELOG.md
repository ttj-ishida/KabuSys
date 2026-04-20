# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
リリースはセマンティックバージョニングに従います。

最新のリリース
----------------

Unreleased
: （なし）

[0.1.0] - 2026-04-20
-------------------

Added
- 実行／監視用エントリポイントを追加
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV に応じて paper_trading 用の専用 SQLite（data/paper_trading.db）を使用し、MockBrokerClient を利用できるように分離。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番 sqlite_path を使用。
  - 停止制御に data/stop_requested.flag を利用し、PID ファイル出力の仕組みを導入（execution.pid / execution の PID ファイルなど）。

- 設定管理と対話式ウィザード
  - config.py: .env 自動ロード機能を導入（プロジェクトルート検出: .git または pyproject.toml 基準）。.env/.env.local 読み込みの優先順を実装。環境変数の取得ラッパ（Settings クラス）を提供。各種既定値・バリデーション（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等）を実装。
  - config_setup.py: .env の初期作成・更新を支援する対話式ウィザードを追加（秘密項目のマスク表示、既存値の再利用、保存前の確認を含む）。

- 設定検証 CLI
  - validate_config.py: 起動前に .env と config/*.yaml の設定不備を検出する CLI を追加。--strict オプションで警告を失敗扱いにできる。PyYAML が無い場合は YAML 検証をスキップして警告表示。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py: 候補選定（スコア降順・タイブレーク）、等分配・スコア重み配分関数を実装。スコアが全て 0 の場合は等分配にフォールバックし警告を出力。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知のレジームはフォールバックで multiplier=1.0（警告）。
  - portfolio/position_sizing.py: 発注株数計算ロジックを実装（risk_based / equal / score）。単元株（lot_size）考慮、1 銘柄上限・aggregate cap（available_cash）でスケールダウン、手数料/スリッページを想定した cost_buffer の考慮、余剰資金の分配ロジックを実装。

- 分析・レポートツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。指定期間の稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL 判定を行う。デフォルト DB は data/paper_trading.db。閾値はソース内で定義（稼働率 99% など）。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py: 全起動スクリプトで統一して利用できるロギング設定ユーティリティを追加。コンソール出力は stdout（cron/スケジューラ向け）、日次ローテーション（TimedRotatingFileHandler）でファイルに出力。ログディレクトリ生成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: クロスプラットフォームでプロセス優先度（high/normal/low）と CPU affinity を設定するユーティリティを追加。Windows と POSIX（Linux/Mac/FreeBSD）に対応し、設定に失敗した場合は警告を出力してスキップする実装。

- データ処理・リサーチ（着手）
  - research/factor_research.py: モメンタム・ボラティリティ等のファクター計算モジュールを追加（DuckDB 接続を受け取り prices_daily 等のテーブルから計算する設計。モジュールは部分実装あり／進行中）。

Changed
- プロジェクト構成とデフォルトパスの整理
  - DuckDB/SQLite のデフォルトパス、ログディレクトリ、PID/flag の位置を data/、logs/ 配下に統一。
  - run_monitoring と run_execution はプロセス起動時に優先度を高くする（set_process_priority("high")）ことで監視・実行の安定性を向上。

Fixed
- .env パーサの堅牢化（config._parse_env_line）
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い、クォートなしの場合の # を使ったコメント判定等を正しく解析するよう改善。
  - _load_env_file: ファイル読み込み失敗時に警告を出しプロセスを継続。

- logging_setup のハンドラ重複防止
  - 既存ハンドラがある場合は一度 flush/close してから削除し、二重出力を防止するよう修正。

- run_execution/run_monitoring の DB 初期化
  - init_monitoring_db を起動時に呼び出して監視テーブルの存在を保証（冪等）。

Notes / Known issues / TODO
- research/factor_research.py は未完（ファイル途中で切れているため、一部関数が未完成）。今後、DuckDB を使ったファクター計算ロジックの追加・完成が必要。
- position_sizing の price 欠損時の扱いに TODO コメントあり（price が 0 の場合のフォールバック価格の導入検討）。
- paper_trading の検証や ExecutionEngine の細部（ブローカーファクトリ、ExecutionEngine 本体、OrderManager 等）はこの CHANGELOG の対象ファイルに依存するが、本 CHANGELOG は公開 API の概要に基づく要約であり、実装の細部や将来的なインターフェース変更に注意してください。

開発者向けメモ
- .env の自動読み込みはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- validate_config.py を使って起動前に必須環境変数や config/*.yaml の整合性をチェックすることを推奨。
- ログは既定で logs/<app_name>.log に日次ローテーションで保存される。コンテナや CI 環境では LOG_DIR 環境変数で変更可能。

著者: コードベース（推測に基づき作成）  
日付: 2026-04-20