# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
安定版・互換性方針はセマンティックバージョニングに従います。

## [0.1.0] - 2026-04-19

### Added
- 初期リリースとして KabuSys の主要コンポーネントを実装。
  - パッケージバージョンを設定（src/kabusys/__init__.py: __version__ = "0.1.0"）。
- 実行スクリプト / デーモン類
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル data/stop_requested.flag の検出で安全にループ終了。
    - 監視は環境に関わらず本番用 sqlite_path を使用する（監視 DB を分離）。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB（data/paper_trading.db）を使用し、本番 DB と分離。
    - 停止フラグ / PID ファイル管理（data/execution.pid）を実装。
    - スレッドで ExecutionEngine を実行し、停止フラグで graceful shutdown。
- 設定・環境管理
  - Settings クラス（src/kabusys/config.py）
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env のパースで export 形式、クォート、インラインコメント等に対応する堅牢な実装。
    - J-Quants / kabu API / DB パス / paper trading 関連 / 監視しきい値等のプロパティを提供。
    - env 値のバリデーション（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）。
  - config_setup: 対話式ウィザードで .env の初期作成・更新を支援（src/kabusys/config_setup.py）。
    - 入力項目の定義、既存 .env 読み込み、シークレットマスク表示、保存機能を提供。
  - validate_config: 起動前に環境変数・config/*.yaml 等を検証する CLI を追加。
    - --strict オプションで警告を FAIL 扱い（exit 1）にできる。
    - 必須環境変数チェック、KABUSYS_ENV の検証、DB パス・YAML ファイルの存在とパース検査、live 環境向けの追加ガードを実装。
- ロギング・プロセス管理ユーティリティ
  - logging_setup: 統一的なログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout へ StreamHandler、日次ローテーション（TimedRotatingFileHandler）でファイル出力（デフォルト logs/<app_name>.log、30日保持）。
    - 環境変数 LOG_LEVEL / LOG_DIR と引数の優先解決を実装。ログディレクトリ作成失敗時はファイル出力を安全にスキップ。
  - process_priority: プラットフォーム差分を吸収したプロセス優先度設定と CPU affinity 設定を追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux, Darwin, FreeBSD）に対応し、例外発生時は警告ログでスキップ。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
- ポートフォリオ構築モジュール（純粋関数群、DB非依存）
  - portfolio_builder: 候補選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）。
    - スコア順ソートのタイブレーク規則、スコア合計が0の場合のフォールバック処理を実装。
  - risk_adjustment: セクター集中制限とレジーム乗数（apply_sector_cap, calc_regime_multiplier）。
    - 現有ポジション・価格マップを用いたセクター別エクスポージャ計算と候補除外ロジック。
    - レジームに応じた投下資金乗数（bull/neutral/bear）と未知レジームでのフォールバック。
  - position_sizing: 株数決定ロジック（calc_position_sizes）。
    - risk_based / equal / score の配分方式、lot_size 単位への丸め、個別上限・集約上限・コストバッファを考慮したスケーリングと端数処理を実装。
    - open_prices や current_positions の欠損処理、価格が不正な銘柄のスキップ扱い。
- 研究モジュール（骨組み）
  - research/factor_research: ファクター計算モジュール（Momentum, Value, Volatility, Liquidity）を追加（DuckDB を利用して prices_daily / raw_financials を参照する設計）。モジュール設計・定数定義を含む（calc_momentum の実装開始）。
- ツール
  - tools/paper_verification_report: ペーパートレード検証レポート生成スクリプトを追加。
    - SQLite（paper_trading DB）から稼働率・注文成功率・送信率・P95 レイテンシ等を集計し、閾値に基づいて PASS/FAIL レポートを出力。
    - コマンドライン引数 --from / --to / --db をサポート。PAPER_TRADING_SQLITE_PATH 環境変数を尊重。
    - P95 計算ユーティリティ、SQL の日付フィルタ構築、データ欠損時の安全なフォールバックを実装。
- DB 初期化ヘルパー
  - monitoring.monitoring_db:init_monitoring_db を利用して監視用テーブルの存在を保証（冪等に初期化）。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Notes / Implementation decisions
- .env の自動ロードは既存 OS 環境変数を保護する仕組み（protected set）で実装。KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると自動ロードを無効化可能。
- run_monitoring は監視データの整合性のため、KABUSYS_ENV に関わらず settings.sqlite_path（本番監視 DB）を利用する設計。運用上の分離が必要な場合は環境変数で sqlite_path を変更してください。
- Paper Trading（KABUSYS_ENV=paper_trading）は発注ロジックを実運用 DB から切り離し、PAPER_TRADING_SQLITE_PATH を用いることで本番データと完全分離することを意図している。
- ロギングは stdout を優先的に使用しつつ、可能ならファイル出力も行う（cron 等でのリダイレクト対応）。
- process_priority は可能な限り OS 横断で動作するよう配慮してあるが、権限不足や未対応プラットフォームでは警告を出して安全にスキップする。

今後の予定（例）
- factor_research の完全実装（Momentum, Value, Volatility, Liquidity の算出）。
- 戦略・発注パイプラインと統合した end-to-end テスト、より詳細なログ/メトリクス追加。
- 各種設定のさらに厳密なバリデーションと CI での自動チェック。

---
保持ポリシー: 主要リリースごとに要約を記載します。バグ修正や小変更は次回以降のリリースで詳細を追加します。