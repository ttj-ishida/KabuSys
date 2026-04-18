Keep a Changelog 形式に従い、コード内容から推測して本リリースの変更履歴（日本語）を作成しました。

CHANGELOG.md
=============
全般方針:
- 本ログはソースコードからの実装状況・挙動を元に推測して作成しています。実際のコミット履歴がある場合はそちらを優先してください。

[0.1.0] - 2026-04-18
-------------------

Added
- 基本機能を初期実装しパッケージを公開。
  - 実行スクリプト:
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は専用の paper_trading DB（data/paper_trading.db を既定）を使用し MockBrokerClient を利用する挙動を実装。エンジンは別スレッドで実行され、data/stop_requested.flag による停止検知・pid ファイルの管理に対応。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を参照して監視 DB を初期化する。
  - 設定・ユーティリティ:
    - config.py: 環境変数/ .env 自動読み込み機能を実装（.env, .env.local の優先順）。.env のパースロジックはクォート・エスケープやインラインコメントを考慮。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。Settings クラスで各種設定値（DB パス、閾値、環境判定フラグ等）を提供。
    - config_setup.py: 対話式ウィザードで .env を生成・更新する CLI を追加。シークレット項目のマスク表示や既存 .env の読み込み、保存機能を実装。
    - validate_config.py: 起動前に環境変数や config/*.yaml の妥当性をチェックする CLI を追加。--strict モードで警告も失敗扱いにできる。PyYAML 非インストール時の扱い、KABUSYS_ENV=live の追加ガードチェック等を実装。
    - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。stdout への StreamHandler と日次ローテートするファイルハンドラ（logs/<app>.log、30日保持）を設定。LOG_DIR/LOG_LEVEL と引数で上書き可能。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
    - utils/process_priority.py: クロスプラットフォームでプロセス優先度（high/normal/low）や CPU affinity を設定するユーティリティを追加。Windows/Linux/macOS 等での互換性考慮（psutil を利用）、権限不足時は警告を出してスキップ。
  - ポートフォリオ構築関連（純粋関数群、メモリ内計算）:
    - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等分配重み (calc_equal_weights)、スコア加重 (calc_score_weights) を実装。スコアが全て 0 の場合は等分配にフォールバック。
    - portfolio/risk_adjustment.py: セクター集中抑制 (apply_sector_cap) と市場レジームに応じた乗数 (calc_regime_multiplier) を実装。未知のレジームは警告を出してフォールバック。
    - portfolio/position_sizing.py: 単元株丸め、リスクベース／等配分／スコア配分に基づく発注株数計算 (calc_position_sizes) を実装。max_position_pct、max_utilization、lot_size、cost_buffer、aggregate cap のスケールダウンロジックや残差処理（lot 単位で追加配分）を含む。
    - portfolio/__init__.py: 上記関数を公開。
  - 解析・検証ツール:
    - tools/paper_verification_report.py: Paper Trading の取引ログから検証レポートを生成するスクリプトを追加。稼働率、注文成功率（fill rate）、送信率、P95 レイテンシなどを集計し PASS/FAIL 判定を出力。コマンドラインで期間指定（--from/--to）や DB パス指定（--db）可能。PAPER_TRADING_SQLITE_PATH 環境変数に対応。
  - 研究用モジュール（部分実装）:
    - research/factor_research.py: ファクター計算モジュール（モメンタム、ボラティリティ、Value 等の計算方針と定数）を追加。DuckDB 接続を受け prices_daily / raw_financials テーブルから計算する設計。calc_momentum 等の実装を開始（ファイル末尾が途中の形で存在）。

Changed
- なし（初期リリース想定のため「追加」が中心）。

Fixed
- 環境変数パースの堅牢化:
  - config._parse_env_line: export プレフィックス対応、クォート内のバックスラッシュエスケープ、インラインコメントの取り扱いを改善。これにより .env の複雑な値も正しくロード可能。
- run_monitoring.py / run_execution.py: DB 初期化処理で監視テーブルの冪等な初期化（init_monitoring_db 呼び出し）を行うことで、実行時に監視テーブルが存在しないケースを回避。

Notes / Behavioral details
- DB/ファイルパスのデフォルト:
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring): data/monitoring.db
  - Paper trading SQLite: data/paper_trading.db
  - PID / フラグファイル: data/execution.pid, data/stop_requested.flag, data/kill.flag 等
- 環境自動ロード:
  - プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動で読み込む。OS 環境変数は保護され、.env.local は上書き可能。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- ロギング:
  - stdout に出力する仕様（cron/Task Scheduler などで stdout/stderr を一本化する運用を想定）。
- ExecutionEngine のリスク管理:
  - RiskManager のデフォルト設定（max_position_pct=0.20、max_utilization=0.80、rate_limit_per_sec=5、circuit_breaker_errors=10、circuit_breaker_window_sec=60、max_drawdown=0.20 等）をコードで定義。
- 監視ループの堅牢化:
  - MONITOR_POLL_INTERVAL の不正値は警告を出してデフォルト（60 秒）にフォールバック。
  - check_once() の例外はログに例外情報を出力し、次回ポーリングまで待機して継続する。
- Paper Trading と本番の分離:
  - KABUSYS_ENV によって paper_trading 用 DB を分離し、実際のブローカー呼び出しはモック化（MockBrokerClient）して記録を分離する設計。

Known / TODO (検出できる範囲)
- research/factor_research.py は一部が未完（ファイル末尾が途中で終端）。ファクター計算の完全実装・テストが必要。
- position_sizing.calc_position_sizes の価格欠損時の扱い（price が 0.0 の場合にエクスポージャーが過少見積もられる問題）は TODO コメントあり。前日終値等のフォールバック実装が今後の改善点。
- 将来的に銘柄ごとの lot_size 対応や stocks マスタの導入を想定する箇所がある。

開発者向けメモ
- CLI 実行例:
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Execution 起動: python -m kabusys.run_execution
  - Monitoring 起動: python -m kabusys.run_monitoring
  - Paper レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

以上。必要であれば、実際のコミット履歴に合わせて日付や変更点を調整した CHANGELOG のドラフトを作成します。