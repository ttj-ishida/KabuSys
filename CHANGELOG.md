# CHANGELOG

すべての重要な変更点を記録します。このファイルは Keep a Changelog の形式に従います。  
リリース日はリポジトリの現状に基づき推定しています。

## [0.1.0] - 2026-04-19

### Added
- 初期リリース: KabuSys - 日本株自動売買システムの基本コンポーネントを追加。
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は専用のペーパートレード用 SQLite（デフォルト: data/paper_trading.db）を使い、MockBrokerClient 経由で発注を模擬する設計を採用。
    - 起動時にプロセス優先度を "high" に設定し、PID ファイル（data/execution.pid）を扱う。
    - 停止フラグ（data/stop_requested.flag）を監視して安全停止を行う仕組みを提供。
    - ExecutionEngine の構築時に BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler などのコンポーネントを組み立てる。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を含む。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によってポーリング間隔を上書き可能（デフォルト: 60秒）。不正な値（0以下等）はデフォルトにフォールバックして警告出力。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番用 sqlite_path を参照して監視テーブルを初期化する。
    - 停止フラグ（data/stop_requested.flag）でループを終了。
    - DuckDB と SQLite の接続を確立して SystemMonitor に注入。
- 設定管理
  - config.py
    - 環境変数読み込みと Settings クラスを提供。
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。.env と .env.local を読み込み、OS 環境変数は保護（上書き防止）。
    - .env の行パースは export プレフィックス、クォート、エスケープ、インラインコメントなどに対応。
    - 多数の設定プロパティを提供（J-Quants, kabu API, LINE, DB パス, 検知閾値, PID/kill flag パス, PAPER_FILL_MODE 等）。
    - KABUSYS_ENV / LOG_LEVEL 等の検証とデフォルト値を実装。
  - config_setup.py
    - 対話式の .env 作成/更新ウィザードを提供。
    - 主要な設定項目定義、既存 .env の読み込み、対話入力、最終確認およびファイル書き込みを実装。
- 設定検証 CLI
  - validate_config.py
    - 起動前の設定検証ツールを提供。
    - 必須/任意環境変数、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML があれば）パース検証、live 環境向けの追加ガードチェックを実装。
    - --strict モードで警告を FAIL 扱いにできる。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定する共通関数 setup_logging() を追加。
    - ログディレクトリ自動作成、環境変数 LOG_DIR / LOG_LEVEL による設定、ファイルハンドラ作成失敗時のフォールバック動作を実装。
  - utils/process_priority.py
    - プラットフォームに依らずプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を提供。
    - Windows/Linux(macOS 等 POSIX) を吸収し、権限不足や非対応環境では警告を出してスキップする堅牢性を確保。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates（スコア降順、タイブレークに signal_rank）を実装。
    - 等金額配分 calc_equal_weights、スコア加重 calc_score_weights（全スコア 0 の場合は等金額にフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中上限を適用する apply_sector_cap を実装（当日売却予定銘柄を除外可能、"unknown" セクターは無視）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear マッピング、未知レジームは警告と共に 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - 複数の配分方式（"risk_based", "equal", "score"）に対応した発注株数決定ロジックを実装。
    - 単元（lot_size）丸め、1銘柄上限（max_position_pct）、投下上限（max_utilization）、手数料/スリッページ見積り cost_buffer を考慮した aggregate cap（総投資額が利用可能現金を超えた場合のスケーリングと再分配）を実装。
    - データ欠損時のスキップやログ出力による注意喚起を実装。
  - portfolio パッケージの __init__.py で上記関数群を公開。
- リサーチ（未完のファクター計算モジュール）
  - research/factor_research.py
    - DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity 等のファクターを計算する設計（モジュール冒頭に定数と calc_momentum の骨子を実装。以降の実装は継続想定）。
- ツール
  - tools/paper_verification_report.py
    - ペーパートレード結果の検証レポートを生成する CLI ツールを追加。
    - system_status, trade_logs, risk_logs テーブルから稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）などを集計。
    - P95 計算、日付フィルタ（--from, --to）、DB パスの解決（--db / env / デフォルト）を実装。
    - デフォルトの合格基準（稼働率 99%, 成功率 90%, 送信率 95%, P95 レイテンシ 200ms）を定義し、PASS/FAIL 判定を出力する。
- パッケージ初期化
  - __init__.py を追加し、バージョン __version__ = "0.1.0" を定義。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Notes / Implementation details
- データベース
  - 実行系（execution）と監視系（monitoring）で SQLite の扱いが分離されている（paper_trading 用 DB が別に存在）。
  - DuckDB は分析用に両方で利用。
- 環境変数の取り扱い
  - .env の自動読み込みはデフォルトで有効。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env のパースは多くのケース（export, クォート内エスケープ, コメント）に対応している。
- ログ出力
  - コンソール出力は stdout を使用（cron 等で stdout/stderr を一本化する環境への配慮）。
  - ファイル出力が失敗してもコンソールログは確実に動作するよう配慮。
- フォールバック・堅牢性
  - 設定不正やファイル未存在、権限不足などの典型的障害に対して警告を出し、安全に継続するよう設計されている（例: MONITOR_POLL_INTERVAL の不正値や process_priority の権限不足など）。

---

今後のリリースに向けて想定される作業:
- research/factor_research.py の完全実装（各ファクター計算ロジックの完成）。
- ExecutionEngine / SystemMonitor 本体のさらに詳細なテストとエラー処理強化。
- 単体テストの追加と CI の整備。
- ドキュメント（API と設計文書）の拡充。