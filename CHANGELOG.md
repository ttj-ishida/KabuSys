# Changelog

すべての変更は Keep a Changelog の方針に従って記載しています。重要な挙動・設定項目・環境変数の説明を含みます。

## [Unreleased]

## [0.1.0] - 2026-04-20
最初の公開リリース。自動売買システム KabuSys のコア機能、CLI ツール、ユーティリティ群を追加しました。

### Added
- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動するメインスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory により環境に応じたブローカークライアントを生成（モック/実ブローカー切替）。
    - 実行中の停止制御: data/stop_requested.flag を検知してエンジンを停止、data/execution.pid に PID を記録する仕組み。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は実行環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ検知で優雅にループ終了。

- 設定管理・ウィザード・検証
  - config.py: 環境変数読み込み／Settings 抽象化を追加。
    - .env 自動読み込み（プロジェクトルートに基づく）。優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - 必須値取得ヘルパーや各種プロパティ（PAPER_FILL_MODE、パス設定、閾値、env/log level 判定等）を提供。
    - PAPER_FILL_MODE の有効値チェック（instant/partial/never/reject）。
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加。
    - 必要項目のプロンプト、既存 .env の読み込み、シークレット項目のマスク表示、保存機能を実装。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数/パス/ログレベル/config/*.yaml の存在と YAML パース検証（PyYAML が存在する場合）を行う。
    - --strict オプションで警告を失敗扱いにできる。

- ロギング / プロセス設定
  - utils/logging_setup.py: 統一的なロギングセットアップを追加。
    - コンソール（stdout）出力と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - ログレベル/ログディレクトリの解決順をサポート。
  - utils/process_priority.py: プロセス優先度（high/normal/low）と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX の差分を吸収し、安全にフォールバックする実装。
    - アクセス権限不足等の例外を警告ログでスキップ。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で候補選定
    - calc_equal_weights, calc_score_weights: 重み化ロジック（score が全て 0 の場合のフォールバック警告含む）
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中を防ぐフィルタ（"unknown" セクターは除外しない挙動）
    - calc_regime_multiplier: レジームに基づく資金乗数（bull/neutral/bear 対応、未知レジームはフォールバック）
  - portfolio/position_sizing.py
    - calc_position_sizes: risk_based / equal / score 各方式に対応した株数算出
    - 単元（lot_size）丸め、per-stock 上限、aggregate cap（利用可能現金を超える場合のスケーリング）、
      cost_buffer による保守的見積り、および残差処理による追加配分ロジックを実装

- 分析・検証ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。
    - PAPER_TRADING_SQLITE_PATH（または --db）から SQLite を参照し、稼働率・注文成功率・送信率・レイテンシ（P95）等を集計。
    - パス/デフォルト閾値（稼働率 99%、成功率 90% 等）に基づく PASS/FAIL 判定を出力。
    - 日付フィルタ（--from/--to）をサポート。

- 研究用モジュール
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールを追加（モメンタム、MA、ATR、出来高等を想定）。
    - DuckDB 接続を受け prices_daily / raw_financials を参照して計算する設計方針。

- パッケージメタ
  - __init__.py にバージョン __version__ = "0.1.0" を追加。

### Changed
- なし（初回リリースのため変更履歴なし）

### Fixed
- なし（初回リリースのため修正履歴なし）

### Notes / Configuration
- 環境変数（主なもの）
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - PAPER_FILL_MODE: instant / partial / never / reject（Paper Trading 時の挙動）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - DUCKDB_PATH（分析 DB、デフォルト: data/kabusys.duckdb）
  - LOG_LEVEL, LOG_DIR
  - MONITOR_POLL_INTERVAL（監視ループのポーリング秒数、デフォルト: 60）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で .env の自動読み込みを無効化可能

- 依存（実行時に必要となる外部ライブラリ）
  - duckdb（DuckDB 接続）
  - psutil（プロセス優先度 / CPU affinity）
  - （任意）PyYAML：config/*.yaml のパース検証に使用（未インストール時は検証をスキップ）

- ログ出力
  - デフォルトで logs/ ディレクトリに日次ローテートされたログファイルを出力。ディレクトリ作成に失敗した場合は標準出力のみで継続。

- 停止制御（共通パターン）
  - data/stop_requested.flag の存在を監視してプロセスを安全に停止する仕組みを使用（run_execution / run_monitoring）。

---

今後の予定（例）
- factor_research の各ファクター計算法の完成とユニットテスト整備
- ブローカーインターフェースの統合テスト、発注フローの耐障害性改善
- 監視・アラート（LINE）連携強化

問題・改善点を発見した場合は Issue を作成してください。