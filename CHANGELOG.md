CHANGELOG
=========

このプロジェクトの変更履歴は「Keep a Changelog」形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- なし

[0.1.0] - 2026-04-21
--------------------

Added
- 初期リリース（バージョン 0.1.0）。
- コア実行スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）へ記録して本番 DB と完全分離する挙動をサポート。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority を使用）。
    - PID ファイル（data/execution.pid）および停止フラグ（data/stop_requested.flag）を扱う制御を実装。
    - ExecutionEngine の実行を別スレッドで行い、停止フラグ検知で安全に停止するループを実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書きをサポート（デフォルト 60 秒、0 以下はデフォルトにフォールバック）。
    - 監視は環境に関わらず本番用 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ検知・KeyboardInterrupt を考慮した安全な終了処理を実装。
- 設定管理
  - config.py: 環境変数 / .env 読み込み機能を実装。
    - プロジェクトルート検出（.git または pyproject.toml を基準）により .env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env パーサは export プレフィックス、クォート文字列、インラインコメントなどを適切に処理。
    - Settings クラスを提供し、J-Quants / kabuAPI / DB パス /監視閾値 / 環境 (development/paper_trading/live) などの取得を容易にする。
    - PAPER_FILL_MODE（instant/partial/never/reject）や PAPER_TRADING_SQLITE_PATH 等の paper_trading 関連設定をサポート。
- 設定ユーティリティ・CLI
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を追加。
    - 秘匿値のマスク表示、選択肢・デフォルト対応、保存確認などを実装。
  - validate_config.py: 起動前に .env と config/*.yaml の整合性を検証する CLI を追加。
    - --strict オプションで警告も失敗扱いにできる。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、YAML パースチェック（PyYAML があれば）を実装。
    - 本番環境向けの追加ガード（LINE 通知設定未設定、KILL_FLAG_CLEAR_ON_START の警告等）を検出。
- ロギング・プロセス設定ユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を用いたファイル出力（デフォルト logs/、30 日分保存）をルートロガーに設定。
    - LOG_DIR/LOG_LEVEL の環境変数または引数で上書き可能。ディレクトリ作成失敗時はファイル出力をスキップしてコンソールにフォールバック。
    - stdout を使用することで cron 等からのリダイレクト運用を想定。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX(Linux, Darwin, FreeBSD) を吸収し、nice 値や Windows の priority class を設定。失敗した場合は警告を出して継続。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順で候補選定（タイブレークに signal_rank）。
    - calc_equal_weights / calc_score_weights: 等配分およびスコア加重配分（スコア合計が 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限を実装（既存保有時価を元に上限超過セクターを遮断）。
    - calc_regime_multiplier: 市場レジーム(bull/neutral/bear) に応じた投下資金乗数を返す。
  - portfolio/position_sizing.py:
    - calc_position_sizes: リスクベース / 等配分 / スコア配分に対応した発注株数計算を実装。単元株丸め、ポジション上限、利用可能現金に対するスケーリング（aggregate cap）、コストバッファ対応を実装。
    - lot_size 将来的拡張のための TODO コメントあり（銘柄別 lot_size への拡張予定）。
  - portfolio/__init__.py で主要関数群をエクスポート。
- research/factor_research.py
  - DuckDB を利用したファクター計算モジュールを追加（モメンタム、MA200乖離、ATR、流動性などを想定）。
  - DuckDB 接続を受け取り価格・財務テーブルのみ参照する設計（発注 API にアクセスしない）。
- ツール群
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。
    - 指定期間（--from/--to）や DB パス（--db / 環境変数）を指定可能。
    - 稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を算出し、閾値（稼働率 99%、成立率 90%、送信率 95%、P95 latency 200ms）に基づく PASS/FAIL 判定を出力。
- DB 統合
  - DuckDB（分析用）と SQLite（監視 / 発注履歴用）の両方をサポートする設計を採用。
  - 監視関連のテーブル初期化を行う init_monitoring_db を run スクリプトで呼び出し、監視テーブルの存在を保証（冪等性）。
- パッケージ情報
  - __init__.__version__ を "0.1.0" に設定。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Removed
- なし（初回リリース）

Security
- なし（初回リリース）

Notes / Known limitations
- position_sizing の lot_size は現状全銘柄共通での扱い。将来的に銘柄毎の lot_map を受け取る拡張を計画。
- research/factor_research モジュールの一部（ファクター計算の続き）は実装途中の箇所がある（コードの一部が切れている箇所あり）。
- .env 自動読み込みはプロジェクトルートが検出できない場合はスキップされる。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

-- End of changelog --