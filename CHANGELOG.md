# Changelog

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠します。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-22
初回リリース。以下の主要機能・ユーティリティ群を追加しました。

### Added
- 実行エントリスクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用の専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離して動作する（MockBrokerClient を利用する想定）。
    - 起動時にプロセス優先度を "high" に設定し、PID ファイル管理・停止フラグ（data/stop_requested.flag）に対応。
    - 各依存コンポーネント（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine）を組み立ててデーモンスレッドで実行、停止フラグ検知で安全に停止する処理を実装。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視は環境に関係なく本番用 sqlite_path を使用（監視テーブルの初期化を実行）。
    - DuckDB と SQLite の接続管理、停止フラグ検知、例外発生時のログ出力・継続動作を備える。

- 設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
    - .env/.env.local の読み込み順序と既存 OS 環境変数の保護機能（protected）に対応。
    - .env の行パーサを実装（export 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い等を考慮）。
    - Settings クラスを提供し、環境変数をプロパティ経由で型変換・バリデーション付きで取得可能（env 判定、log_level、DB パス、paper trading など）。

  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を実装。
    - シークレット項目はマスク表示、選択肢／デフォルトの提示、既存 .env の読み込み・再利用をサポート。
    - 保存前に設定内容を確認し、テンプレート形式で .env を出力する。

  - validate_config.py
    - 起動前に .env および config/*.yaml の設定不備を検出する検証ツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在および PyYAML があれば構文チェックを実施。
    - --strict オプションで警告も失敗（exit 1）にできる。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルの候補選定 select_candidates（スコア降順、タイブレークに signal_rank）。
    - 等重み calc_equal_weights、スコア加重 calc_score_weights（全てのスコアが 0 の場合は等重みへフォールバック）を実装。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限をチェックして候補から除外するロジックを実装（sell_codes を除外して既存保有のセクターエクスポージャを計算）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返すユーティリティを実装（未知レジームは警告を出して 1.0 にフォールバック）。

  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算を実装。
    - 単元（lot_size）、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap のスケーリング、余剰キャッシュでの端数処理（lot 単位で再配分）を実装。
    - 価格欠損時のログ、ゼロ除算回避や保守的見積り（cost_buffer）を考慮。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加（setup_logging）。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次・30世代保持）をルートロガーに設定。ログディレクトリの解決順と作成失敗時のフォールバックを実装。
    - LOG_LEVEL 環境変数や引数でレベルを解決。

  - utils/process_priority.py
    - set_process_priority: Windows / POSIX の差を吸収してプロセス優先度を設定（HIGH/NORMAL/LOW）。権限不足や未対応 OS の場合は警告を出してスキップ。
    - set_cpu_affinity: 指定したコア数にプロセスをピン留めするユーティリティ（存在しない環境や権限不足は警告でスキップ）。

- 監視・検証ツール
  - monitoring/monitoring_db の初期化呼び出しを実行して監視テーブルの存在を保証（冪等）。
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成ツールを追加。
    - レポートはシステム稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、API レイテンシ（avg/max/P95）などを算出し PASS/FAIL を判定。
    - CLI オプション --from / --to / --db をサポート。P95 の計算や日付フィルタの組み立てを実装。
    - デフォルトで PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）を参照。

- 研究用モジュール（骨組み）
  - research/factor_research.py
    - Momentum/Value/Volatility/Liquidity などのファクター計算モジュールの骨組みと定数を追加。DuckDB 接続を受けて prices_daily / raw_financials を参照する想定の実装設計を導入（モジュールの一部は継続実装予定）。

- パッケージ初期設定
  - __init__.py にバージョン __version__ = "0.1.0" を追加。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Security
- なし

補足:
- 本リリースはコードベースの初期公開に相当するもので、実運用向けには更なるテストやドキュメント整備（Strategy/Engine の細部、Broker 実装、monitoring の詳細なアラート設定など）が推奨されます。