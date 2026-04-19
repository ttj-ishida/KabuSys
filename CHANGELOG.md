# Changelog

すべての注記は Keep a Changelog の形式に従います。  
リリース日付は 2026-04-19。

## [Unreleased]
- （現在未リリースの変更はここに記載）

## [0.1.0] - 2026-04-19

### Added
- 初回公開リリース。
- 基本アプリケーションパッケージ (kabusys) を追加。
  - バージョン情報: __version__ = "0.1.0"（src/kabusys/__init__.py）。

- 実行 / 監視用起動スクリプトを追加。
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper_trading SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) を利用した安全停止機構。
    - BrokerClientFactory、OrderManager、OrderRepository、RiskManager、Reconciler、ExecutionEngine の組み立てロジックを搭載。
    - RiskConfig のデフォルト値を設定し、初期資金は broker.get_available_cash() から取得。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は監視用 SQLite（settings.sqlite_path）を常に使用（KABUSYS_ENV に依存しない）。
    - 停止フラグ検知でループ終了、KeyboardInterrupt に対応。

- 設定管理・支援ツールを追加。
  - config.py
    - .env の自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - 強力な .env パースロジック（export 形式やクォート、インラインコメント処理対応）。
    - Settings クラスで環境変数をプロパティ経由で取得（必須チェックや値検証を含む）。
    - デフォルトパス、Paper Trading 用パス、しきい値設定などを提供。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成 / 更新する CLI。
    - 複数の設定項目（KABUSYS_ENV、J-Quants / kabu API 認証、DB パス、LINE トークンなど）をサポート。
    - 既存 .env の読み込み、保存確認、.env 書き出しを実装。
  - validate_config.py
    - 起動前に .env と config/*.yaml の基本チェックを行う CLI。
    - 必須環境変数の未設定チェック、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在チェック、YAML パースチェック（PyYAML が存在する場合）など。
    - --strict を指定すると警告も失敗（exit 1）として扱う。

- ポートフォリオ構築関連モジュールを追加（純粋関数群）。
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を提供。
    - スコア合計が 0 の場合は等金額配分にフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）。
    - セクター不明 ("unknown") は上限適用対象外。
    - 不明レジームは 1.0 でフォールバック（警告ログ）。
  - portfolio/position_sizing.py
    - weight / equal / risk_based の allocation method に対応した株数決定ロジック。
    - 単元（lot_size）、max_position_pct、max_utilization、cost_buffer（手数料・スリッページ見積り）を考慮した aggregate cap スケーリング。
    - lot_size 単位で切り捨て／再配分を行うアルゴリズムを実装（端数処理・優先度の安定性を考慮）。

- サポートユーティリティを追加。
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定する共通ユーティリティ。
    - LOG_DIR / LOG_LEVEL の解決順を実装、ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - Windows / POSIX の差分を吸収したプロセス優先度設定（set_process_priority）。
    - CPU affinity を設定する set_cpu_affinity（psutil ベース）。
    - 権限不足や未対応 OS でも安全にスキップするロバスト性を確保。

- 監視用 DB 初期化フックを追加（monitoring.monitoring_db.init_monitoring_db を run スクリプトから呼び出し）。
- Paper Trading 検証レポート生成ツールを追加。
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から統計を集計してレポート出力。
    - 稼働率 (uptime)、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を算出し、PASS/FAIL 判定を行う閾値を定義。
    - 日付フィルタ、コマンドラインオプション（--from, --to, --db）に対応。

- 研究用ファクタ計算モジュールを追加（research/factor_research.py、未完の実装開始）。
  - DuckDB 接続を受け取り prices_daily / raw_financials を参照してモメンタム・バリュー等ファクタを計算する設計を導入（関数 calc_momentum の骨組みを含む）。

### Changed
- （初回リリースのため、過去からの変更は無し）

### Fixed
- （初回リリースのため、修正履歴は無し）

### Deprecated
- （無し）

### Removed
- （無し）

### Security
- （特記事項無し）

### 注意事項 / 既知の問題
- .env 自動読み込みはプロジェクトルートが検出できない場合はスキップされます。テスト環境で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- config.Settings のプロパティは未設定時に ValueError を送出するものがあります（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）。起動前に validate_config を実行して設定を確認してください。
- run_execution.py は初期化時に broker.get_available_cash() を RiskConfig.initial_portfolio_value に使用します。Broker 実装の挙動に依存します。
- portfolio/risk_adjustment.apply_sector_cap 内の price 欠損時の挙動について TODO コメントあり。価格が 0.0 の場合は過少見積りのリスクがあるため、将来的にフォールバック価格の導入を検討しています。
- process_priority の設定は OS 権限に依存します。権限不足時は警告ログを出力して処理をスキップします。
- research/factor_research.py は一部実装が途中（ファイル末尾で切れている）です。実運用で使用する前に関数の完成とユニットテストを推奨します。
- ログディレクトリ作成やファイルハンドラ作成に失敗した場合、ログはコンソール（stdout）に出力されます。ログファイルを利用する場合は LOG_DIR の書き込み権限を確認してください。

---

このリリースは初期実装をまとめたものです。今後のリリースでは以下を予定しています:
- research/factor_research の完成と最適化
- ExecutionEngine / BrokerClient の追加テストとエラーハンドリング強化
- 監視・アラート（LINE）連携の拡充
- 個別銘柄の lot_size 管理や手数料・スリッページの詳細モデル化

ご不明点や追加で changelog に反映したい差分があればお知らせください。