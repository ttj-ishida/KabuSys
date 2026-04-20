Keep a Changelog
すべての変更は https://keepachangelog.com/ja/ に準拠しています。

Unreleased
---------
- （未リリースの変更はここに記載します）

[0.1.0] - 2026-04-20
-------------------
Added
- 初期リリース: KabuSys 自動売買システムの基本機能を実装。
  - 設定管理:
    - .env の自動読み込み（.env.local が .env をオーバーライド、OS 環境変数は保護）。
    - Settings クラスを導入し、環境変数から各種設定値を取得するプロパティを提供（J-Quants / kabu API / DB パス / 各種監視閾値 など）。
    - PAPER_FILL_MODE の値検証（instant/partial/never/reject）や KABUSYS_ENV / LOG_LEVEL の検証を実装。
  - 設定補助ツール:
    - config_setup CLI: 対話式ウィザードで .env を作成・更新する機能を追加。
    - validate_config CLI: .env と config/*.yaml を起動前に検証する機能を追加（--strict による厳格モード対応）。
  - 起動スクリプト:
    - run_execution: ExecutionEngine 起動スクリプトを実装。KABUSYS_ENV=paper_trading 時は paper_trading 用 DB と MockBroker を利用し本番 DB と分離。停止フラグ / PID ファイルハンドリング・デーモンスレッド管理を含む。
    - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視は環境にかかわらず本番 sqlite_path を使用。
  - ロギング・プロセス優先度:
    - utils.logging_setup: stdout に出力する StreamHandler と日次ローテーションする TimedRotatingFileHandler をルートロガーに設定するユーティリティを追加。LOG_DIR / LOG_LEVEL による設定、既存ハンドラのクリアなどを実装。
    - utils.process_priority: Windows / POSIX の差分を吸収してプロセス優先度と CPU affinity を設定するユーティリティを追加。権限不足時には警告を出してスキップ。
  - ポートフォリオ構築（純粋関数）:
    - portfolio.portfolio_builder: 候補選定（select_candidates）、等配分 / スコア加重（calc_equal_weights / calc_score_weights）。
    - portfolio.risk_adjustment: セクター上限フィルタ（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）。
    - portfolio.position_sizing: 発注株数計算ロジック（calc_position_sizes）。リスクベース・等配分・スコア配分、単元株丸め、aggregate cap によるスケールダウン処理を実装。
  - 解析・検証ツール:
    - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（P95 など）を集計し PASS/FAIL を判定する。
  - DB 初期化:
    - 監視用 DB テーブルの初期化（init_monitoring_db）の呼び出しを起動スクリプトに組み込み。
  - パッケージメタ:
    - パッケージバージョンを __version__ = "0.1.0" として設定。

Fixed
- .env パーサの堅牢化:
  - export KEY=... 形式のサポート、シングル/ダブルクォート内のバックスラッシュエスケープ処理、行内コメントの取り扱い（クォート有無での挙動差異）などを実装。
  - .env ファイル読み込み時に OS 環境変数を保護する protected 引数を追加し、意図せぬ上書きを防止。
- run_monitoring の MONITOR_POLL_INTERVAL の不正値処理:
  - 0 以下や非整数の値が指定された場合にデフォルト値（60 秒）へフォールバックし、警告を出すように修正。
- ロギング初期化の堅牢化:
  - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソール出力のみで継続するように変更（start-up failure を回避）。
- process_priority / set_cpu_affinity: 権限不足や未対応 OS に対する例外処理を追加し、失敗時は警告ログを出して処理を続行。

Changed
- run_execution/run_monitoring の挙動整理:
  - どちらも起動時にプロセス優先度を最初に "high" に設定するよう統一。
  - run_execution は paper_trading モードのとき専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離する明確な仕様に。
  - run_monitoring は監視用途の DB 初期化と DuckDB 接続の確立を行うように整理。

Security
- 環境変数管理に関する注意事項を config_setup の出力ヘッダに明記（.env を絶対に Git にコミットしないこと）。

Notes / migration
- .env の自動読み込みはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。パッケージ配布後やテスト時に自動ロードを無効化したい場合はこのフラグを設定してください。
- Paper Trading を実行する場合は KABUSYS_ENV=paper_trading を設定すると paper_trading 用 DB（デフォルト data/paper_trading.db）と MockBrokerClient が使用され、本番 DB と完全に分離されます。
- run_monitoring は常に Settings.sqlite_path（本番監視 DB）を使用します。監視データの格納先を切り替えたい場合は環境変数 SQLITE_PATH を設定してください。
- MONITOR_POLL_INTERVAL（秒）で監視ポーリング間隔を指定可能。無効な値は 60 秒にフォールバックします。

Acknowledgments
- 本リリースは多数のユーティリティ関数、起動スクリプト、純粋関数群（ポートフォリオ構築）および検証ツールを含む初期実装です。追加のユニットテスト、ドキュメント、Strategy / Execution の具体的実装は今後のリリースで拡充予定です。