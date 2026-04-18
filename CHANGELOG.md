# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
慣例: 変更は種類別に分類（Added, Changed, Fixed, Deprecated, Removed, Security）しています。

## [Unreleased]

## [0.1.0] - 2026-04-18
初期リリース。

### Added
- 基本アプリケーションパッケージとバージョン情報を追加
  - package: kabusys, __version__ = 0.1.0

- 環境・設定管理
  - .env 自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml から検出）
  - .env / .env.local の読み込みルール:
    - OS 環境変数を保護（既存値は上書きされない）
    - .env.local は .env を上書き可能
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能
  - .env ファイルのパース機能を実装（export プレフィックス、シングル/ダブルクォート、エスケープ、行内コメントの扱いに対応）
  - Settings クラスを実装し、環境変数の取得・検証を提供（例: KABUSYS_ENV、PAPER_FILL_MODE の検証、DB パス、ログ設定、監視閾値など）

- 設定支援 CLI
  - config_setup ウィザード: 対話式に .env を生成 / 更新する CLI を追加
    - 入力プロンプト、既存値の再利用、シークレットマスキング、選択肢、確認・保存機能を備える
  - validate_config CLI: 起動前に .env と config/*.yaml の簡易検証を行うツールを追加
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パス親ディレクトリチェック
    - PyYAML がインストールされていれば config/*.yaml のパース検証も実行
    - --strict オプションで警告も失敗扱いにできる

- 起動スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（data/paper_trading.db を想定）を使用（本番 DB と分離）
    - BrokerClientFactory 経由でブローカークライアントを生成（MockBrokerClient の利用が可能）
    - Engine の起動・デーモン化スレッド化、停止フラグ（data/stop_requested.flag）による安全停止、pid ファイル管理
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit breaker 等）を組み込み
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
    - 監視は環境にかかわらず本番 sqlite_path を利用する設計（monitoring 用 DB 初期化を保証）
    - 停止フラグ検出・例外耐性・リソースクリーンアップを実装

- ロギング / プロセス優先度ユーティリティ
  - utils.logging_setup.setup_logging を追加
    - stdout（StreamHandler）と日次ローテート (TimedRotatingFileHandler) をルートロガーに設定
    - LOG_LEVEL / LOG_DIR の解決順を実装し、ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続
  - utils.process_priority.set_process_priority / set_cpu_affinity を追加
    - Windows と POSIX を透過的に扱い、権限不足や未対応 OS は警告を出してスキップ
    - set_cpu_affinity によりプロセスを最初の N コアにピンニング可能

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順・タイブレーク条件で候補選定
    - calc_equal_weights, calc_score_weights: 重み計算（スコア全0時は等配分にフォールバック）
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限を適用する関数（既存保有を考慮、"unknown" セクターは制限対象外）
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear のマッピング、未知レジームは警告してフォールバック）
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づく発注株数計算
      - 単元株（lot_size）に丸め、1銘柄上限や aggregate cap、コストバッファ考慮、可用資金に合わせたスケーリング、残差分のロット配分ロジックを実装

- Research / ツール
  - research.factor_research: DuckDB を利用したファクター計算モジュール（Momentum, Value, Volatility, Liquidity を想定。prices_daily / raw_financials を参照）
  - tools.paper_verification_report: ペーパートレード検証レポート生成スクリプトを追加
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、リスク却下数、API レイテンシ（avg/max/P95）
    - 閾値・PASS/FAIL 判定ロジックを備える（デフォルト閾値はコード内で定義）
    - --from / --to / --db オプションをサポート

- DB 初期化ユーティリティ
  - monitoring.monitoring_db.init_monitoring_db を参照して、監視用テーブルの存在を保証する処理を各起動スクリプトから呼び出し

### Changed
- none（初回リリースのため変更履歴はありません）

### Fixed
- none（初回リリース）

### Notes / 詳細
- 設定パースの堅牢性
  - .env のクォート付き値でバックスラッシュエスケープを正しく処理するなど、複雑なケースを考慮
- Paper Trading の分離
  - run_execution は paper_trading モードで専用 SQLite を使用し、本番 DB とは完全分離される設計
- 監視周り
  - run_monitoring は監視 DB のパスとして Settings.sqlite_path を使用する（監視は本番 DB を参照する想定）
- ログ出力は標準化され、起動スクリプト間で統一的に利用することを想定
- 一部モジュール内に TODO / 将来拡張のコメントあり（例: position_sizing の銘柄別 lot_size 対応、risk_adjustment の価格フォールバック）

---

今後のリリースでは、以下を予定しています（未実装/拡張案）:
- strategy 実装の統合（シグナル生成・バックテスト連携）
- Broker クライアントの詳細実装とテスト向けモックの整備
- DuckDB を用いた一括集計処理の追加最適化
- 単体テスト・統合テストの追加、CI パイプライン統合

（必要であれば、各ファイルごとの細かい変更点や実装上の注意点を追記します。）