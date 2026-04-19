# Changelog

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
バージョン番号はパッケージ内の __version__（src/kabusys/__init__.py）に基づきます。

## [0.1.0] - 2026-04-19

### Added
- 初回リリース。日本株自動売買システム「KabuSys」のコア機能群を追加。
- 起動スクリプト
  - run_execution: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV に応じてペーパートレード用の MockBrokerClient を使用し、paper_trading 環境では data/paper_trading.db を専用 DB として分離して動作する。停止フラグ (data/stop_requested.flag) と PID ファイル機構を備える。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は本番 sqlite_path を使用する設計。
- 設定管理
  - config.Settings: 環境変数 / .env 自動読み込み機能（.env / .env.local、OS 環境変数保護機構を含む）を実装。多くの設定（DB パス、ログレベル、ペーパートレード設定、各閾値など）をプロパティで提供。
  - config_setup: .env 初期作成・更新のための対話式ウィザード CLI を追加（python -m kabusys.config_setup）。
  - validate_config: .env と config/*.yaml の起動前検証 CLI を追加（python -m kabusys.validate_config）。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検証、DB パスの親ディレクトリチェック、YAML のパースチェック（PyYAML 任意）などを実行。--strict モードで警告を FAIL 扱いにできる。
- ロギング・プロセス管理ユーティリティ
  - utils.logging_setup.setup_logging: stdout 出力 + 日次ローテート（TimedRotatingFileHandler）でログを統一。ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。デフォルトで 30 日分を保持。
  - utils.process_priority: プロセス優先度（high/normal/low）と CPU affinity 設定のユーティリティを追加。Windows/Linux/Mac の差分を吸収。権限不足時は警告を出して安全にスキップ。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: 候補選定（スコア降順）、等金額配分、スコア加重配分（スコア合計が 0 の場合は等配分にフォールバック）を実装。
  - portfolio.risk_adjustment: セクター集中制限を行う apply_sector_cap と、市況レジームに応じた資金乗数を返す calc_regime_multiplier を実装（regime: bull/neutral/bear のハンドリング、未知レジームはフォールバック）。
  - portfolio.position_sizing: ポジションサイズ算出（risk_based / equal / score）を実装。単元株丸め、1 銘柄上限・aggregate cap（available_cash）適用、cost_buffer（手数料・スリッページ見積り）を考慮したスケーリングロジックを含む。
- 解析 / 運用ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均 / 最大 / P95）を集計し PASS/FAIL 判定を行う。閾値はソース内で定義（例: 稼働率 >= 99%、P95 <= 200 ms）。コマンドライン引数で期間指定可能。
- 研究用モジュール（部分実装）
  - research.factor_research: DuckDB を用いたファクター計算の基盤（モメンタム、MA200 乖離など）の骨格を追加。prices_daily / raw_financials テーブルを参照する設計。

### Changed
- N/A（初回リリースのため特段の変更履歴なし）

### Fixed
- N/A（初回リリース）

### Security
- 環境変数の自動ロードでは OS 環境変数が保護される設計（.env の上書きは protected キーを考慮）。また .env の生成ウィザードは .env をコミットしない旨の注意を明示。

### Notes / Usage highlights
- 起動スクリプト:
  - 実行例: python -m kabusys.run_execution、python -m kabusys.run_monitoring
  - 停止: プロジェクトルートの data/stop_requested.flag を作成すると両プロセスは安全に停止する。
- 環境変数主要項目:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須。
  - KABUSYS_ENV: development / paper_trading / live（無効値は例外）。
  - PAPER_FILL_MODE: instant / partial / never / reject（デフォルト: instant）。
  - MONITOR_POLL_INTERVAL: 監視ポーリング秒数（整数、デフォルト 60 秒）。
  - KILL_FLAG_CLEAR_ON_START: 本番環境での自動クリアは注意喚起（validate_config が警告）。
- ログ:
  - デフォルトは logs/<app_name>.log を日次ローテートで保存（30 日保持）。LOG_DIR / LOG_LEVEL で変更可能。

もしリリースノートをさらに分割（例: "Breaking changes", "Migration notes"）したり、日付や担当者情報を追記したい場合は指示してください。