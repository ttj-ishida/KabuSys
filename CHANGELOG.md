# Changelog

すべての変更は Keep a Changelog のフォーマットに従います。  
このプロジェクトはセマンティックバージョニングを採用します。

注: 下記はリポジトリ内のコード内容から推測して作成した変更ログです。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-20
初回リリース。日本株自動売買システム「KabuSys」の基礎機能を実装しました。

### Added
- 実行スクリプト
  - run_execution: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading 時にモックブローカーを使用し、ペーパートレード用 DB（デフォルト: data/paper_trading.db）と完全分離して動作する構成を提供。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) に対応し、安全な停止処理を実装。
    - RiskManager / OrderManager / Reconciler 等の依存コンポーネントを組み立てて ExecutionEngine を実行するスレッド管理を実装。

  - run_monitoring: SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - 監視は常に本番用 sqlite_path を使用する（環境に依存しない）。
    - 停止フラグ (data/stop_requested.flag) を検知してループ終了。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.Settings クラスを実装。環境変数から各種設定を取得・検証。
    - J-Quants / kabu API / LINE / DB パス / 監視閾値 / システム設定などのプロパティを提供。
    - KABUSYS_ENV, LOG_LEVEL などの値検証を実施。
    - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等のペーパートレード向け設定を追加。

  - .env 自動ロード機能を実装（.env, .env.local）。  
    - プロジェクトルート自動検出（.git / pyproject.toml 基準）。  
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサはシングル/ダブルクォート、export プレフィックス、インラインコメント等を考慮。

- 設定ユーティリティ / CLI
  - config_setup: 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。
    - 必須/任意・シークレット項目の案内、保存確認、デフォルト/既存値の再利用に対応。
  - validate_config: 起動前に .env と config/*.yaml の検証を行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パス周りのチェック、YAML ファイルの存在・パース検証（PyYAML が利用可能な場合）。
    - --strict オプションで警告も FAIL 扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - utils.logging_setup.setup_logging を追加。
    - stdout 出力用 StreamHandler と、日次ローテーション（TimedRotatingFileHandler）でログをファイルに出力（デフォルト logs/<app_name>.log、30 日分保持）。
    - LOG_DIR / LOG_LEVEL の環境変数や引数で上書き可能。
    - ログディレクトリ作成失敗時はファイルハンドラを省略して stdout のみで継続。

  - utils.process_priority: プロセス優先度設定と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX（Linux, macOS, FreeBSD）を透過的に扱い、権限不足や未対応環境では安全にフォールバック。

- ポートフォリオ構築ライブラリ (pure functions)
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルのスコア降順フィルタ。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重の重み計算（スコア全て 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限（既存ポジション比率に基づく候補除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear 等）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく注文株数計算。
    - lot_size（単元株）対応、1銘柄上限、aggregate cap（利用可能現金に基づくスケーリング）、cost_buffer（手数料・スリッページ見積り）対応。

- 監査・検証ツール
  - tools.paper_verification_report: ペーパートレード DB を解析して稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを出力するレポート生成スクリプトを追加。
    - デフォルト閾値を定義（稼働率 >= 99%, 成功率 >= 90% 等）し、PASS/FAIL 判定を行う。
    - --from / --to / --db で期間・DB を指定可能。

- データ探索 / 研究スケルトン
  - research.factor_research: ファクター計算モジュールの骨格を追加（Momentum / Value / Volatility / Liquidity を想定）。
    - DuckDB 接続を受けて prices_daily / raw_financials を参照して計算する設計。
    - 実装は一部（モメンタム計算の先頭）まで含まれる（今後拡張予定）。

### Changed
- なし（初回リリースのため既存コードの大規模追加が主）。

### Fixed
- なし（初回リリース）。

### Known limitations / Notes
- research.factor_research はまだ一部実装（未完の関数が存在する可能性）。研究用モジュールは今後拡張予定。
- process_priority / set_cpu_affinity は権限や OS に依存する操作を行うため、実行環境によっては設定に失敗して警告を出してスキップします（安全にフォールバック）。
- .env ファイルは機密情報を含むため絶対に Git にコミットしないでください（config_setup の出力にも同様の注意書きあり）。
- monitoring は「監視 DB」として sqlite_path を常に使用する設計のため、本番/ペーパーで共通の監視 DB を想定しています。必要に応じて運用方針に合わせて分離してください。

---

（将来のリリースでは機能追加・バグ修正・ドキュメント強化等の履歴をここに追記してください。）