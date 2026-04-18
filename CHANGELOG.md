CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。セマンティックバージョニングを想定しています。

Unreleased
----------

- 現在なし。

0.1.0 - 2026-04-18
------------------

Added
- 初回リリース: KabuSys v0.1.0 を追加。
- 環境設定 / 起動スクリプト
  - config.Settings: 環境変数を集中管理する Settings クラスを実装。多数のプロパティ（J-Quants / kabu API / DB パス / ログ設定 / 監視閾値等）を提供。
  - 自動 .env ロード: プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動読み込み。既存の OS 環境変数を保護する仕組みを搭載（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - config_setup: 対話式ウィザード（python -m kabusys.config_setup）で .env を生成・更新するツールを追加。デフォルトや説明文付きで初期設定を支援。
  - validate_config: 起動前に .env / config/*.yaml 等の設定を検証する CLI（--strict オプションで警告も FAIL 扱い）。必須環境変数チェック、DB パスの存在確認、YAML パース確認（PyYAML がある場合）などを実施。

- 実行系 / 監視
  - run_execution: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）に対応。別スレッドでエンジンを実行し、停止フラグ検出時に安全に停止。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は起動環境に関わらず本番 sqlite_path を使用する仕様。
  - 監視 DB 初期化: monitoring テーブルを初期化する init_monitoring_db 呼び出しを両スクリプトで実行（冪等）。

- ブローカー・エンジン周辺
  - BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager 等の起動時組み立て処理を run_execution に実装。RiskManager 用のデフォルト RiskConfig 値（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を設定。initial_portfolio_value はブローカから取得。
  - ExecutionEngine は duckdb と sqlite の接続を受け取り、PID ファイル管理と graceful shutdown を実装。

- ロギング / プロセス管理ユーティリティ
  - utils.logging_setup.setup_logging: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定する共通ユーティリティ。LOG_LEVEL / LOG_DIR の解決順をサポートし、ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみ動作するフォールバック。
  - utils.process_priority: プラットフォーム差分を吸収する set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。Windows / POSIX(nice) に対応し、失敗時は警告を出してスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: シグナル選定関数 select_candidates、等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights を実装。
  - portfolio.risk_adjustment: セクター集中制限 apply_sector_cap と市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（未定義レジームはフォールバック）。
  - portfolio.position_sizing: 株数決定ロジック calc_position_sizes を実装。allocation_method に "risk_based", "equal", "score" をサポート。単元株（lot_size）丸め、per-position 上限、aggregate cap（利用可能現金を超えた場合のスケーリング）、cost_buffer（手数料/スリッページ保守見積）を考慮したアルゴリズムを含む。スケーリング時の残差処理（lot 単位での再配分）も実装。

- リサーチ / ファクター計算
  - research.factor_research: DuckDB 接続を受けて Momentum / Value / Volatility / Liquidity 系ファクターを計算するためのモジュールを追加（calc_momentum 等の実装方針、定数を定義）。（注: ファイルは一部に続きあり）

- ツール
  - tools.paper_verification_report: ペーパートレーディング結果を集計・判定する CLI を追加。PAPER_TRADING_SQLITE_PATH を参照（--db オプションで上書き可）。稼働率、注文成功率、送信率、レイテンシ（P95）等を計算し PASS/FAIL を出力する閾値を定義（稼働率 99% 等）。

- パッケージ情報
  - パッケージ初期バージョン __version__ = "0.1.0" を設定。

Changed
- （初回リリースにつき該当なし）

Fixed
- .env パーサーの堅牢化:
  - quoted 値のエスケープ処理や export プレフィックス対応、インラインコメント取り扱いを実装。
  - .env の読み込み時に既存 OS 環境変数を保護する仕組みを導入（.env.local は上書き可能だが protected により OS env の上書きを防止）。
- ログ設定で既存ハンドラを二重に登録しないよう、セットアップ時に既存ハンドラを flush/close して削除するように修正。

Security, Notes
- .env は絶対に Git にコミットしない旨を config_setup の出力に明記。
- validate_config による起動前チェックを推奨（特に KABUSYS_ENV=live の場合は複数の警告チェックを行う）。

開発者向けメモ
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数（秒）でポーリング周期を変更可能。1 未満・不正値はデフォルト 60 秒にフォールバック。
- run_execution は paper_trading モードでは paper_sqlite_path を使い、本番データベースと完全分離する設計。
- calc_position_sizes の将来的拡張点:
  - 銘柄別の lot_size をサポートするため stocks マスタとの連携を想定した拡張がコメントに残されています。

既知の制限
- research.factor_research の実装はファイル末尾で途中（続き）になっている箇所があり、実装完了状況によっては追加作業が必要です。
- 一部の環境依存機能（プロセス優先度設定、CPU affinity）は権限や OS により失敗する可能性があり、失敗時はログ警告でスキップします。

--- 

（以降のリリースでは Breaking Changes / Added / Changed / Fixed / Security に分類して追記してください）