CHANGELOG
=========

すべての重要な変更を記録します。フォーマットは "Keep a Changelog" の慣例に準拠しています。

履歴
----

Unreleased
~~~~~~~~~~

- （なし）

0.1.0 - 2026-04-19
~~~~~~~~~~~~~~~~~~

Added
- パッケージ初期リリース: kabusys v0.1.0 を追加。
- 実行用スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の Paper Trading SQLite（デフォルト: data/paper_trading.db）を使用して本番データと分離。
    - 実行中は data/execution.pid を利用（PID ファイルパスは設定で上書き可能）。
    - 停止制御に data/stop_requested.flag を利用。停止フラグを検知したらエンジンに停止を通知。
    - BrokerClientFactory を使ったブローカークライアント生成、OrderRepository／OrderManager／RiskManager／Reconciler の組み立てを行う。
    - RiskConfig のデフォルト値（max_position_pct, max_utilization, rate_limit_per_sec 等）を設定して起動。
- 監視用スクリプト
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はログ警告の上でデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path（設定の sqlite_path）を使用して監視テーブルを初期化。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
    - 例外発生時はログに例外トレースを残して次のポーリングまで待機。
- 設定管理
  - config.py: 環境変数・設定管理を追加。
    - .env/.env.local の自動読み込み機能（プロジェクトルートが特定できる場合）。OS 環境変数は保護。
    - export KEY=val、クォート文字列、インラインコメント等に対応する .env パーサ実装。
    - Settings クラスで各種設定値をプロパティとして提供（J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / 環境判定等）。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
- 設定ユーティリティ・CLI
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - .env の読み取り、既存値の再利用、秘密値のマスク表示、保存機能を提供。
    - デフォルト値・選択肢・説明を内蔵。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml 存在・パースチェック（PyYAML が利用可能な場合）。
    - --strict オプションで警告を FAIL 扱いにできる。
- ロギング・プロセスユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。
    - stdout（StreamHandler）と日次ローテートのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップして警告を出力。
  - utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX 系（Linux / macOS / FreeBSD）を吸収する実装。
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(n) を提供。権限不足などは警告ログでフェイルソフト。
- ポートフォリオ構築ライブラリ（純関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で候補選定（タイブレーク: signal_rank 昇順）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア正規化配分。スコア合計が 0 の場合は等配分にフォールバック（警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクターごとの既存エクスポージャーに基づき新規候補の除外処理を実装（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）を提供。未知レジームは警告後 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づく発注株数計算を実装。
    - リスクベースの計算、lot_size（単元株）での丸め、1 銘柄上限・aggregate cap（利用可能現金を超えた場合のスケーリング）や残差処理を実装。
    - cost_buffer を加味して保守的にコスト見積り（スリッページ・手数料の想定）を可能に。
- 解析・検証ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。
    - PAPER_TRADING_SQLITE_PATH（または --db）で指定した SQLite から集計してレポート出力。
    - システム稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、API レイテンシ（avg/max/P95）等を算出。
    - デフォルトの合格基準（稼働率 >= 99.0%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200ms）を定義し PASS/FAIL を判定。
    - --from / --to による期間指定をサポート。
- 研究モジュール（ファクター計算の土台）
  - research/factor_research.py: DuckDB 接続を受け取り Momentum / Value / Volatility / Liquidity の計算方針を実装するための骨組みを追加（モジュールの一部が実装途中）。
    - モメンタム指標（1M/3M/6M リターン、MA200 乖離等）の計算方針と定数を定義。
- パッケージ初期化
  - __init__.py: バージョン情報 __version__ = "0.1.0" を追加。パッケージ公開 API を __all__ で定義。

Changed
- （初回リリースにつきなし）

Fixed
- （初回リリースにつきなし）

Deprecated
- （初回リリースにつきなし）

Removed
- （初回リリースにつきなし）

Security
- （初回リリースにつきなし）

Notes / Known limitations / TODO
- research/factor_research.py は一部未完（ファイル末尾で切れている状態）。完全なファクター計算ロジックは今後の実装予定。
- position_sizing.calc_position_sizes、risk_adjustment.apply_sector_cap などに価格欠損時のフォールバック（前日終値や取得原価を用いる等）の TODO コメントあり。価格データ欠損時の挙動に注意。
- process_priority の優先度設定や CPU affinity は権限やプラットフォームによっては実行できないことがあり、その場合は警告を出してスキップする設計。
- .env 自動読み込みはプロジェクトルート検出（.git または pyproject.toml）に依存する。自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定する。
- run_monitoring/run_execution は内部で monitoring.system_monitor などのモジュールを参照するが、リポジトリ内に全ての実装が含まれていない場合は起動時に ImportError となる可能性がある（実行前に依存モジュールの存在を確認してください）。

運用メモ（簡易）
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- Paper レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

クレジット
- 初期実装: コア構成（設定管理、実行/監視ランナー、ポートフォリオ構築、ロギング・プロセスユーティリティ、検証・セットアップツール、Paper レポート、研究モジュールのスケルトン）。