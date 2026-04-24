CHANGELOG
=========

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

0.1.0 - 2026-04-24
------------------

Added
- 主要コンポーネントの初期実装を追加。
  - 実行/監視ランナー
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、SQLite/DuckDB 接続、ブローカークライアント生成、ExecutionEngine の起動・停止制御（stop flag / PID ファイル対応）を提供。
      - KABUSYS_ENV=paper_trading のときは paper_trading 用 SQLite（data/paper_trading.db）を使用し、MockBrokerClient を想定した分離を行う（BrokerClientFactory に基づく）。
    - run_monitoring.py: SystemMonitor 用のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能（デフォルト: 60 秒）。Monitoring は環境に関わらず本番 sqlite_path を使用する仕様。
  - 設定管理
    - config.py: 環境変数読み込み・ラッパー Settings を実装。自動でプロジェクトルートの .env / .env.local を読み込み（必要に応じて無効化可）、キー毎のデフォルトやバリデーション（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を提供。
    - config_setup.py: 対話式ウィザード(.env 生成/更新)を追加。主要設定項目を網羅し既存 .env の読み込み・編集をサポート。
    - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在と（PyYAML がある場合は）パース検証、本番起動時の安全ガードチェックなどを行う。--strict モードあり。
  - ポートフォリオ構築・リスク調整・サイズ計算（純粋関数群）
    - portfolio/portfolio_builder.py: シグナル選定（スコア降順）、等金額・スコア基準の重み計算を実装。
    - portfolio/risk_adjustment.py: セクター別エクスポージャー上限適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
    - portfolio/position_sizing.py: allocation_method（risk_based / equal / score）に基づく株数算出ロジック、単元株丸め、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的推定などを実装。
    - portfolio/__init__.py でエクスポートを整理。
  - ユーティリティ
    - utils/logging_setup.py: 統一的ログ設定ユーティリティを追加。stdout ストリームハンドラおよび日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）を設定。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - utils/process_priority.py: クロスプラットフォームなプロセス優先度設定（Windows の優先度クラス / POSIX の nice 値）、および CPU affinity 設定ヘルパを追加。権限不足や未対応プラットフォーム時に警告を出して安全にフォールバック。
  - ツール
    - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs テーブルを集計し、稼働率・注文成功率・送信率・レイテンシ（平均・最大・P95）を算出、閾値に基づいて PASS/FAIL 判定を表示。P95 計算ロジックを実装。
  - リサーチ（未完成の箇所含む）
    - research/factor_research.py: ファクター計算モジュールの骨組みを追加（モメンタム・MA200・ATR 等の計算を想定）。DuckDB 接続を受け取り prices_daily / raw_financials テーブルを参照して計算する設計。注: ファイル末尾で一部実装が未完（途中）であり、今後の追加実装を予定。

Changed
- 初期リリースにおける設計方針（ログ管理、環境読み込み、DB 分離方針等）を統一。
  - ログ: stdout に出力する StreamHandler をデフォルトで使い、Task Scheduler/cron の運用を想定した設計に統一。
  - 環境変数読み込み: OS 環境変数を保護（.env/.env.local の上書き制御）する仕組みを導入。

Fixed
- 各種堅牢化（例）
  - 環境変数パーサー(_parse_env_line)でクォート・エスケープ・インラインコメントの取り扱いを改善し、より現実的な .env フォーマットに対応。
  - logging_setup: ログディレクトリ作成やファイルハンドラ生成に失敗した場合でも stdout ログを継続するようにフォールバック処理を追加。
  - process_priority: 未対応 OS や権限不足時に例外崩壊しないよう警告でフォールバック。
  - run_monitoring/run_execution: 停止フラグ検知、例外発生時のログ出力（logger.exception）やリソースクローズ処理を明確化。

Security
- .env を生成する際の注意喚起を config_setup に明記（.env を Git にコミットしないこと）。

Notes / 今後の作業予定
- research/factor_research.py の未完部分（関数の続き・最終実装）を完成させ、DuckDB ベースのファクター計算を実装する。
- ExecutionEngine / SystemMonitor 等の詳細実装（別モジュール）が本リリース外で既に存在している前提だが、実運用に向けた追加テスト・監査を予定。
- 単体テスト、CI ワークフロー、ドキュメント（README、運用手順）を追って追加予定。

開発者向け補足
- 自動 .env 読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途等）。
- デフォルトの DB/ログパスなどは Settings クラスのプロパティで確認できます（SQLITE_PATH, DUCKDB_PATH, LOG_DIR 等）。
- Paper Trading の挙動は Settings.is_paper を用いて切り分けられており、paper 用 DB は PAPER_TRADING_SQLITE_PATH 環境変数で上書き可能。

----- 

（初回公開バージョン）