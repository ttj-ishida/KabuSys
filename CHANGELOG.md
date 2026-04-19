CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠します。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-19
--------------------

Added
- 基本アプリケーションおよびユーティリティ群を初回リリース。
  - src/kabusys/__init__.py にバージョン情報を追加（__version__ = "0.1.0"）。
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するメインスクリプトを追加。paper_trading 環境時は paper_sqlite_path を使用して本番 DB と分離する動作を想定（BrokerClientFactory により MockBrokerClient を生成する想定）。停止フラグ / data/execution.pid の扱い、デーモンスレッドでのセッション実行と優雅な停止処理を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。
- 設定管理 / ヘルパー
  - config.py: 環境変数読み込みと Settings クラスを実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を起点）。
    - .env/.env.local の自動読み込み（OS 環境変数を保護して上書き制御）。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env パーサーは export 付き行、クォート文字列とバックスラッシュエスケープ、インラインコメント扱い（クォートあり/なしの差異）に対応。
    - 各種設定プロパティ（DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE の検証、PID/kill flag パス、閾値設定など）を提供。
  - config_setup.py: .env 作成・更新の対話式ウィザードを追加。既存 .env の取込み、シークレット入力のマスク、保存前確認、.env を上書きして保存する機能を提供。
  - validate_config.py: 設定検証 CLI を追加。必須環境変数や config/*.yaml の存在・パース検証、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、--strict モード（警告を FAIL 扱い）対応。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定関数 setup_logging を追加。コンソール (stdout) と日次ローテートファイルハンドラをルートロガーへ設定、ログディレクトリ自動作成や失敗時のフォールバックを考慮。
  - utils/process_priority.py: プロセス優先度設定 (set_process_priority) と CPU affinity 設定 (set_cpu_affinity) を追加。Windows / POSIX の差分を吸収し、安全に失敗を無視する実装（psutil を使用）。
- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア重み (calc_score_weights) を実装。スコア合計が 0 の場合は等配分へフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限 (apply_sector_cap)、市場レジームに応じた乗数 (calc_regime_multiplier) を実装。未知レジーム時はフォールバック挙動を定義。
  - portfolio/position_sizing.py: 発注株数計算 (calc_position_sizes) を実装。risk_based / equal / score の割当方式、単元株 (lot_size) 丸め、単銘柄上限・合計投下上限・cost_buffer を用いたスケールダウンロジック、残余キャッシュを用いた切り上げ配分の戦略を備える。
  - portfolio/__init__.py: 上記関数をエクスポート。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から検証レポートを生成する CLI を追加。期間指定 (--from / --to) に対応し、システム稼働率、注文成功率・送信率、リスク却下数、レイテンシ (avg/max/P95) を算出。閾値に基づく PASS/FAIL を出力。
- 研究用ファクター計算（開発中）
  - research/factor_research.py: Momentum / Value / Volatility / Liquidity 等のファクター計算モジュールを追加（DuckDB 接続を受け prices_daily / raw_financials を参照する設計）。モメンタム計算関数 calc_momentum の実装を開始（未完の箇所あり）。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Notes / 注意点
- run_monitoring はドキュメントどおり MONITOR_POLL_INTERVAL でポーリング間隔を変更可能。0 以下や不正な値はデフォルト 60 秒にフォールバックして警告を出す動作。
- run_monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path（本番監視 DB）を使うため、環境による DB 分離が必要な場合は注意。
- run_execution は paper_trading 環境で paper_sqlite_path を使用する（data/paper_trading.db がデフォルト）ことで、本番 DB と記録を分離する設計。
- .env 自動読み込みはプロジェクトルートが検出できない場合はスキップされる（配布後のパッケージ環境などで安全）。
- research/factor_research.py は一部実装が継続中のため、完全な機能提供は今後のリリースで行う予定。

Acknowledgements
- 本リリースはシステム起動スクリプト、設定管理、ロギング/プロセス制御、ポートフォリオ構築ロジック、Paper Trading 検証ツールといった基盤機能を提供します。今後、strategy 実行部分や broker 実装、ファクター計算の完成、テスト追加、ドキュメント整備を進めていきます。