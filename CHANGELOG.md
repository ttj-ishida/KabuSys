# Changelog

すべての重要な変更履歴を記録します。本ファイルは「Keep a Changelog」フォーマットに準拠しています。  

注意: 以下の変更内容はリポジトリに含まれるソースコードから推測して作成したものです。

## [Unreleased]

（現在のところ未リリースの変更はありません）

## [0.1.0] - 2026-04-19

初回公開リリース。自動売買システム「KabuSys」の基盤機能を実装しました。以下の主要機能・改善点を含みます。

### Added
- 全体
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。
  - プロジェクトの起動スクリプト、ユーティリティ、ポートフォリオ構築、研究用ファクター計算、運用支援ツール等の初期実装を追加。

- 起動 / 実行
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用のペーパートレード SQLite を使用して本番 DB と分離。
    - BrokerClient の生成、OrderRepository、OrderManager、RiskManager（初期設定含む）、Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止処理を実装。
    - 実行 PID ファイルの扱い（pid ファイルパス）をサポート。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番の sqlite_path を使用して監視情報を記録。

- 設定 / 検証
  - config.py: 環境変数・設定管理モジュールを実装。
    - .env ファイルの自動読み込み（プロジェクトルート検出: .git または pyproject.toml）を実装。
    - export 構文やシングル/ダブルクォート、インラインコメントのパースに対応するカスタム .env パーサを実装。
    - 各種設定プロパティ（DB パス、PID/kill フラグ、閾値、PAPER_FILL_MODE など）を提供。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - シークレット値のマスク表示、デフォルト値・選択肢の提示、.env の書き出しをサポート。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パスと config/*.yaml の存在・パース検証、live 向けガード（LINE 設定や Kill フラグ挙動）を実装。
    - --strict モードで警告を FAIL 扱いにできる。

- ポートフォリオ構築（Portfolio）
  - portfolio.portfolio_builder:
    - select_candidates(): BUY シグナルをスコア降順で選別するユーティリティ。
    - calc_equal_weights(), calc_score_weights(): 等分配・スコア加重の重み計算。スコア合計が 0 の場合は等分配にフォールバック（警告出力）。
  - portfolio.risk_adjustment:
    - apply_sector_cap(): セクター集中を制限するフィルタ。既存ポジションからセクター別エクスポージャを算出して上限超過セクターは新規候補から除外。
    - calc_regime_multiplier(): 市場レジーム（bull/neutral/bear）に応じて投下資金乗数を返す。未知レジームは警告後 1.0 でフォールバック。
  - portfolio.position_sizing:
    - calc_position_sizes(): 重み・候補・価格・現在ポジション等から銘柄ごとの発注株数を計算。
    - risk_based / equal / score の割当方式をサポート。lot_size 単位丸め、単銘柄上限、aggregate cap によるスケーリング（残差配分ロジック含む）、手数料・スリッページを考慮する cost_buffer をサポート。

- 研究・ファクター
  - research.factor_research: モメンタム等のファクター計算モジュール（DuckDB を用いた価格・財務データ参照設計）。
    - モメンタム指標（1M/3M/6M、MA200 乖離）などの計算ロジックを示す実装（部分的に実装中、設計と初期関数あり）。

- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定（閾値はソース内定数で定義）。
    - 日付フィルタ（--from / --to）、DB パス指定（--db または PAPER_TRADING_SQLITE_PATH）をサポート。
  
- ユーティリティ
  - utils.logging_setup:
    - 統一したロギング初期化関数 setup_logging() を実装。
    - stdout への StreamHandler と日次ローテートする TimedRotatingFileHandler（logs/<app_name>.log）を設定。ログディレクトリ作成失敗時はファイル出力をスキップしコンソールのみで継続。
  - utils.process_priority:
    - set_process_priority(): Windows（HIGH_PRIORITY_CLASS 等）と POSIX（nice 値）を吸収して優先度を設定。失敗時は警告を出してスキップ。
    - set_cpu_affinity(): 指定コア数で CPU affinity を設定（利用可能コア数を超えた場合は全コアを使用）。失敗時は警告。

### Changed
- 初期リリースのため該当なし。

### Fixed
- 初期リリースのため該当なし。

### Deprecated
- 初期リリースのため該当なし。

### Removed
- 初期リリースのため該当なし。

### Security
- 初期リリースのため該当なし。

---

注記・既知の制限・今後の改善案（コードから推測）
- research.factor_research モジュールは設計方針・定義は含まれるが、ファイル末尾で実装が途中になっているため（切り出し箇所あり）完全実装が必要。
- position_sizing の価格フォールバック（価格欠損時の扱い）に TODO コメントあり：前日終値や取得原価などを用いたフォールバックの追加検討が必要。
- .env パーサは多くのケースに対応しているが、非常に複雑な .env の全ケースに対しては追加のエッジケース検証が望ましい。
- ログディレクトリ作成失敗や優先度設定失敗時はアプリは稼働を継続する設計だが、運用環境では権限・パス設定を事前に確認することを推奨。

もし CHANGELOG に追加したい項目（例えばリリース日を固定したくない、あるいはより細かい変更履歴の分割など）があれば指定してください。必要に応じて英語版やセクションの整理も作成します。