Keep a Changelog に準拠した CHANGELOG.md

すべての変更はセマンティックバージョニングに従います。  
詳しい背景や利用方法はソースコード内の docstring / コメントを参照してください。

変更履歴
========

Unreleased
----------

（特になし）

[0.1.0] - 2026-04-20
-------------------

Added
- 初回リリースを追加。
- 環境設定 / ロード
  - .env/.env.local 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
  - .env のパース機能を実装（export 形式、クォート／エスケープ、インラインコメント処理に対応）。
  - Settings クラスを実装し、環境変数経由の設定アクセスを提供（J-Quants / kabu API / DB パス / 各種閾値など）。
  - 環境変数の必須チェックを行う _require 関数と、PAPER_FILL_MODE 等の妥当性検証を実装。
- 設定ウィザード CLI
  - config_setup.py に対話式ウィザードを実装し、.env を安全に初期生成・更新可能（シークレット項目はマスク表示）。
  - 書き出しフォーマットと既存 .env 読み込みをサポート。
- 設定検証 CLI
  - validate_config.py を実装。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の有無と YAML パース（PyYAML 利用可）などを検証。
  - --strict オプションで警告も失敗扱いにできる。
  - 本番環境向けの注意喚起（LINE 通知設定や KILL_FLAG_CLEAR_ON_START）を追加。
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用専用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを行い、ExecutionEngine をスレッドで実行。
    - data/execution.pid（デフォルト）や data/stop_requested.flag による停止処理をサポート。
    - RiskManager のデフォルト設定（max_position_pct 等）を定義し、初期 available cash を broker.get_available_cash() から取得。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバックして警告。
    - 監視は環境にかかわらず本番 sqlite_path を使用する（監視 DB の分離はしない設計）。
    - stop flag file によるループ終了、KeyboardInterrupt のハンドリング、例外発生時のログ出力を実装。
    - 起動直後にプロセス優先度を "high" に設定（set_process_priority を使用）。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30世代保持）を設定。
    - LOG_DIR 指定や LOG_LEVEL 解決順（引数 > 環境変数 > デフォルト）に対応。
    - ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソール出力のみで継続。
  - utils/process_priority.py:
    - Windows/Linux/macOS の差分を吸収してプロセス優先度（high/normal/low）を設定。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity 実装（利用不可時は警告してスキップ）。
    - 権限不足などのケースを安全にハンドリング。
- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順で選定（同スコアは signal_rank でブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分を実装。スコア合計が 0 の場合は等金額へフォールバック（警告）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限（max_sector_pct）に基づき新規候補を除外する機能を実装。売却予定銘柄はエクスポージャー計算から除外。unknown セクターは上限適用対象外。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear、未知は 1.0 でフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた株数計算を実装。
    - 単元（lot_size）で丸め、1 銘柄上限・aggregate cap（available_cash）を考慮したスケーリング、cost_buffer による保守的見積りを実装。
    - 価格未取得銘柄はスキップ、価格 0 の場合の安全処理あり。
- 解析 / リサーチ
  - research/factor_research.py（ファクター計算の骨組みを実装、モメンタム等の定義を含む）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクターを算出する設計（詳細関数は実装中／継続）。
- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用の検証レポート生成ツールを追加。
    - デフォルト DB: data/paper_trading.db、--db オプションや PAPER_TRADING_SQLITE_PATH 環境変数で上書き可。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）、リスク却下数。
    - 基準値（閾値）を定義し、PASS/FAIL 判定を出力（P95 計算、NULL/データ欠損時の N/A 表示含む）。
- パッケージ初期化
  - kabusys.__init__ にバージョン（0.1.0）と __all__ を追加。

Changed
- （なし：初回リリース）

Fixed
- （なし：初回リリース）

Notes / ユーザー向けメモ
- DB パスのデフォルト
  - DuckDB: data/kabusys.duckdb
  - Monitoring SQLite: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
- 環境切り替え
  - Settings.env（KABUSYS_ENV）により is_live / is_paper / is_dev が判定される。実行制御や DB の選択に利用される。
  - run_monitoring は設計上 KABUSYS_ENV にかかわらず monitoring 用に指定された sqlite_path（デフォルト monitoring.db）を使用する点に注意。
- 停止フラグ / PID ファイル
  - stop flag: data/stop_requested.flag（存在検出で監視ループやエンジンを終了）。
  - execution PID: data/execution.pid（ExecutionEngine で使用）。
- ログ
  - stdout を利用する StreamHandler を優先。ログファイル出力は logs/<app_name>.log に日次ローテーションで保存。LOG_DIR 環境変数で変更可。
- セキュリティ注意
  - .env は絶対にリポジトリにコミットしないこと。
  - config_setup により生成される .env に機密情報が含まれる点に注意。
- 既知の制限 / TODO
  - position_sizing の price フォールバックが未実装（価格欠損時の見積り改善が TODO）。
  - research/factor_research の一部関数は継続実装中。

参考コマンド
- 設定ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

ライセンスやその他のメタ情報はリポジトリのルートを参照してください。