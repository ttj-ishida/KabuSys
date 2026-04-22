CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-04-22

### Added
- 初期リリースを追加。
- 実行用スクリプト / 実行エンジン
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを提供。
    - KABUSYS_ENV=paper_trading の場合は本番 DB と完全に分離された paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient を利用する設計を想定。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine を起動。
    - RiskManager 用のデフォルト RiskConfig を定義（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20 等）。initial_portfolio_value は broker.get_available_cash() から取得。
    - エンジンは別スレッドで実行し、 data/stop_requested.flag による停止、実行中の PID を data/execution.pid に扱う想定。
    - 起動前に監視用テーブルが存在することを保証するため init_monitoring_db を呼び出す（冪等）。

- 監視用スクリプト
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを提供。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正な値はデフォルトにフォールバックして警告を出力。
    - Monitoring は KABUSYS_ENV に関わらず本番用 sqlite_path を使用（監視用 DB として data/monitoring.db を想定）。
    - プロセス優先度を "high" に設定して起動（set_process_priority を使用）。
    - duckdb への接続を行い、SystemMonitor.check_once() を定期的に呼び出す。停止フラグ（data/stop_requested.flag）検知で終了。

- 設定管理
  - src/kabusys/config.py
    - .env / .env.local の自動読み込み（プロジェクトルートが特定可能な場合、OS 環境変数優先。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env パーサは export プレフィックス、単一/二重引用符、バックスラッシュエスケープ、インラインコメント等に対応。
    - Settings クラスを提供し、アプリケーション設定をプロパティとして取得可能（例: jquants_refresh_token, kabu_api_password, duckdb_path, sqlite_path, paper_sqlite_path, paper_fill_mode 等）。
    - PAPER_FILL_MODE のバリデーション（有効値: "instant"|"partial"|"never"|"reject"）。
    - KABUSYS_ENV の検証（development, paper_trading, live）と補助プロパティ is_live / is_paper / is_dev。
    - 監視・キルフラグ関連の設定（pid_file_path, kill_flag_path, kill_flag_clear_on_start）や閾値設定（cpu/memory/disk）。

- 設定ウィザード・検証 CLI
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を生成・更新するユーティリティ。秘密項目はマスク表示、既存値の再利用、保存確認をサポート。
  - src/kabusys/validate_config.py
    - .env や config/*.yaml の起動前検証ツール。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、PyYAML があれば YAML のパース検証を行う。
    - 本番 (live) 向けの追加警告（LINE 設定や KILL_FLAG_CLEAR_ON_START の危険性）。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定するユーティリティ。
    - LOG_LEVEL/LOG_DIR の優先順位に従って設定。ディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - src/kabusys/utils/process_priority.py
    - psutil を用いて Windows/Linux/Mac の差分を吸収したプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を提供。権限不足や未対応 OS の場合は警告を出して継続。

- ポートフォリオ構築モジュール
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で上位 N 件を選択する関数。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分を計算。スコア合計が 0 の場合は等配分にフォールバックして警告。
  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中（max_sector_pct）に基づいて当日の候補をフィルタリング。sell_codes（当日売却予定銘柄）を除外してエクスポージャーを計算。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（デフォルトマップ: bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは警告して 1.0 をフォールバック。
  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes: weights/candidates/portfolio_value/available_cash 等を基に各銘柄の発注株数を計算。allocation_method は "risk_based" / "equal" / "score" をサポート。
    - lot_size（単元株）に基づく丸め、per-stock 上限（max_position_pct）、aggregate cap（available_cash）を尊重し、コストバッファ（cost_buffer）を加味したスケーリングと残差による追加配分ロジックを実装。

- Paper Trading 検証ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用 SQLite（環境変数: PAPER_TRADING_SQLITE_PATH）から検証レポートを生成する CLI。
    - システム稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を集計し、閾値（例: uptime >= 99%, fill_rate >= 90%, P95 <= 200ms）に基づいて PASS/FAIL 判定を行う。
    - --from / --to / --db オプションをサポート。

- 研究用ファクター計算
  - src/kabusys/research/factor_research.py（実装を開始）
    - Momentum / Value / Volatility / Liquidity といったファクター群を計算する設計。DuckDB の prices_daily / raw_financials を参照する方針。
    - モメンタム計算関数 calc_momentum の実装が着手されている（詳細はコード内コメントを参照）。

- パッケージメタ
  - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を追加。
  - パッケージエクスポートに portfolio 関連 API を追加（kabusys.portfolio.*）。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Known issues / Notes
- apply_sector_cap 内の価格欠損時の扱いに TODO コメントあり：price が 0.0 の場合にエクスポージャーが過少見積りされる可能性があるため、将来的に前日終値などのフォールバックを検討する旨が記載されている。
- ログディレクトリ作成や process priority 設定は環境によって失敗する可能性があり、その場合は警告を出してフォールバック（コンソールのみ出力 / 優先度設定をスキップ）する設計。
- research/factor_research.py の実装は一部未完（ファイル末尾が途中で切れている）。研究モジュールは今後の追加実装が必要。

### Security
- （現時点で特筆すべきセキュリティ修正なし）

-----
以上。必要に応じて各項目を細分化して追記します。