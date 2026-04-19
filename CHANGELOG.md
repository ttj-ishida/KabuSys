CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[0.1.0] - 2026-04-19
--------------------

Added
- 初期リリース。基本的な自動売買システムのコア機能を実装。
- 起動用スクリプト
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。プロセス優先度を上げ、PID ファイル管理、停止フラグによる安全停止をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書きをサポート。監視は環境に依らず本番用 sqlite_path を使用。
- 環境設定・検証ツール
  - config_setup.py: 対話式 .env ウィザードを実装。主要な環境変数を生成・更新可能。
  - validate_config.py: .env と config/*.yaml を検証する CLI を追加。--strict オプションで警告も失敗扱いにできる。
- 設定管理
  - config.py: .env 自動ロード機能を実装（.env, .env.local の読み込み順序をサポート）。export 形式やクォート、インラインコメントを扱う堅牢なパーサを実装。Settings クラスでアプリケーション設定をプロパティとして提供（env, log_level, DB パス、paper_trading 関連設定、監視閾値など）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）を追加。
    - paper_trading 用の PAPER_TRADING_SQLITE_PATH をサポート。
    - kill_flag 関連や閾値（CPU/MEM/DISK）のプロパティを追加。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等重み・スコア重み付け (calc_equal_weights, calc_score_weights) を実装。
  - portfolio/risk_adjustment.py: セクター集中制限の適用 (apply_sector_cap)、市場レジームに基づく乗数計算 (calc_regime_multiplier) を実装。
  - portfolio/position_sizing.py: 発注株数計算（risk_based / equal / score）、単元株丸め、aggregate cap スケーリング、コストバッファ考慮を実装。
- 実行系コンポーネント（参照・組立て）
  - run_execution にて BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組立てを行う実装を追加（設定例: RiskConfig のデフォルト値など）。
  - Paper trading 環境では専用 SQLite（data/paper_trading.db など）を使用し、本番 DB と分離。
- 監視系
  - monitoring 初期化用関数 init_monitoring_db を呼び出す実装（SQLite / DuckDB の接続確保）。
  - SystemMonitor の単発チェック呼び出し（monitor.check_once()）をポーリングで実行し、例外時にログを残して次回ポーリングへ継続。
- ログ・プロセスユーティリティ
  - utils/logging_setup.py: stdout ストリームハンドラと日次ローテートファイルハンドラ（TimedRotatingFileHandler）を統一的に設定するセットアップ関数を追加。ログディレクトリ自動作成と環境変数優先ルールを持つ。
  - utils/process_priority.py: psutil を用いたプラットフォーム非依存のプロセス優先度設定（high/normal/low）と CPU affinity 設定を実装。アクセス権限がない場合は警告でスキップ。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等の指標を集計し PASS/FAIL 判定を出力。閾値はソース内定義（例: uptime >= 99%、fill_rate >= 90% など）。
- データ分析基盤
  - DuckDB 統合: DuckDB 接続を受け取り分析用テーブル（prices_daily, raw_financials 等）を扱う設計を採用（research モジュールのファクター計算に着手）。
- パッケージ情報
  - __init__.py: パッケージバージョンを "0.1.0" に設定。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Notes / Implementation details
- 停止制御: プロジェクトルート以下 data/stop_requested.flag を存在確認して停止する仕組み（run_execution と run_monitoring 共通）。ExecutionEngine は起動前にフラグが立っていれば起動を回避する。
- PID / ロック: run_execution は data/execution.pid を PID ファイルとして使用する想定（ExecutionEngine に渡す）。
- DB 初期化: 監視テーブルの存在を保証するため、起動時に init_monitoring_db(sqlite_conn) を呼び出す（冪等性を意識）。
- ログ: ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存され、標準出力は stdout に出力される（cron 等でのリダイレクトを想定）。
- Paper Trading 分離: paper_trading 環境では MockBrokerClient 想定のクライアントが使用され、データは専用の paper_trading DB に記録されることで本番 DB とは完全に分離される設計。
- 設定パーサ: .env の読み込みは OS 環境変数を保護する仕組み（protected set）を持ち、.env.local は .env を上書きする（ただし既存 OS 環境変数は上書きしない）。

Known limitations / TODOs
- research/factor_research.py はファクター計算の実装方針と一部定数および関数の開始があるが（ファイル末尾が途中で切れている）、完全な実装は未完（今後の追加実装予定）。
- position_sizing の lot_size は現状グローバル固定（将来的に銘柄別単元対応を検討）。
- 一部の fallback 動作（価格欠損時の扱い、過少データ時のフォールバック等）は TODO コメントで示されている。

開発・運用メモ
- 本リリースは初期の骨格実装を提供します。実トレード運用に入る前に validate_config で設定の検証、config_setup で .env を整え、Paper Trading で動作検証を十分に実施してください。
- 本番運用時は KABUSYS_ENV=live を設定する際に LINE 通知設定や KILL フラグの取り扱いに注意してください（validate_config に警告チェックあり）。

-- END --