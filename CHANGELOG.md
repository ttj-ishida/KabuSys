# Changelog

すべての注目すべき変更点を記録します。形式は "Keep a Changelog" に準拠しています。

## [0.1.0] - 2026-04-19

初回リリース。KabuSys の基本コンポーネント群を追加しました。

### 追加
- コアランタイム／起動スクリプト
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ file: data/stop_requested.flag を検出してループを終了。
    - Monitoring は環境（KABUSYS_ENV）に関わらず production の sqlite_path を使用。
    - sqlite3 と DuckDB の両方に接続して動作。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite DB（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory により実運用/モックブローカーを切り替え。
    - スレッドでエンジンを実行し、停止フラグ検知で安全停止。
    - 実行 PID ファイル管理（data/execution.pid）に対応。

- 設定・環境管理
  - config.Settings クラスを追加。環境変数から各種設定（DB パス、API トークン、閾値等）を取得。
    - env（KABUSYS_ENV）のバリデーション（development / paper_trading / live）。
    - paper_trading 用の PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等をサポート。
    - 監視閾値（CPU/MEM/DISK）や PID / kill flag パス等のプロパティを提供。
  - 自動 .env ロード機能を追加（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - OS 環境変数を保護して .env / .env.local を読み込む。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
    - .env のパースにおいてクォートやエスケープ、インラインコメントの取り扱いを実装。

- 設定支援 CLI
  - config_setup: 対話式ウィザードで .env ファイルを生成・更新する CLI を追加。
    - シークレット項目のマスク表示、既存 .env の読み込み／再利用、デフォルト値提示。
    - .env のテンプレート出力機能を提供。
  - validate_config: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DB パス・YAML ファイル存在確認、live 環境向けガードを実装。
    - --strict オプションで警告を FAIL 扱いに可能。
    - PyYAML が未インストールの場合は YAML 検証をスキップして警告を表示。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルのスコア降順ソートと上位選定を実装。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重重みの計算。スコア合計が 0 の場合は等配分へフォールバック。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限（既存保有分を考慮して候補を除外）。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear とフォールバック）を実装。
  - portfolio.position_sizing
    - calc_position_sizes: risk_based / equal / score の各配分方式に対応した発注株数計算（lot_size 単位、aggregate cap スケーリング、cost_buffer 考慮等）。

- ユーティリティ
  - utils.logging_setup: 一貫したロギング設定ユーティリティを追加。
    - stdout（StreamHandler）と日次ローテーションファイル（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ自動作成、LOG_DIR/LOG_LEVEL 環境変数または引数で上書き可能。ファイル出力障害時はコンソールのみで続行。
    - デフォルトログディレクトリ: logs/、30 日分保持。
  - utils.process_priority: Windows/Linux/macOS を吸収するプロセス優先度・CPU affinity 設定ユーティリティを追加。
    - set_process_priority(level): high/normal/low の抽象レベルを提供。権限不足等は警告してスキップ。
    - set_cpu_affinity(cpu_count): 最初の N コアに固定する機能。未対応/権限不足は警告してスキップ。

- 分析・レポート
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（fill/send）、リスク却下数、API レイテンシ（平均/最大/P95）などを算出・表示。
    - 閾値による Pass/Fail 判定（デフォルト: uptime >= 99%、fill >= 90%、send >= 95%、P95 <= 200 ms）。
    - --from / --to / --db オプション対応。PAPER_TRADING_SQLITE_PATH 環境変数対応。

- 研究（リサーチ）基盤（初期実装）
  - research.factor_research モジュールを追加（モメンタム等のファクター計算実装の骨格）。
    - DuckDB 接続を受け、prices_daily / raw_financials を参照して各種ファクターを計算する設計方針を採用。
    - （注）factor_research は継続実装中（ソース末尾で途中切れの痕跡あり）。

- パッケージメタ
  - パッケージ初期バージョンを設定: __version__ = "0.1.0"

### 変更
- 起動スクリプト共通の挙動
  - 起動直後にプロセス優先度を "high" に設定する呼び出しを追加（set_process_priority("high")）。
  - 監視/実行プロセスの停止フラグ検知（data/stop_requested.flag）と PID ファイル管理の扱いを明確化。

### 修正（実装時の注意／既知の挙動）
- .env パーサはクォート内のバックスラッシュエスケープやインラインコメントの扱いを独自実装しており、非常に柔軟に動作するが、極端に特殊な書式の .env は想定外の動作をする可能性がある。
- apply_sector_cap: price_map に価格が欠損（0.0 等）の場合、エクスポージャーが過少見積もられる可能性があり将来的なフォールバック改善を注記。
- process_priority / set_cpu_affinity は権限不足やプラットフォーム非対応時に警告を出してスキップする設計（安全第一）。

---

今後の予定（例）
- research.factor_research の完遂（ファクター計算の SQL 実装）
- ExecutionEngine / Broker の詳細なテスト・シミュレーション強化
- ツール類のレポート出力フォーマット（CSV/JSON）の追加

（この CHANGELOG はコードベースからの推測に基づき記載しています。実際のリリースノートとして利用する際は必要に応じて加筆修正してください。）