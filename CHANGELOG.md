# Changelog

すべての変更は "Keep a Changelog" の形式に従い記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-16

Added
- パッケージ初期リリース。
- 基本情報
  - パッケージメタ情報を追加: kabusys/__init__.py に __version__ = "0.1.0" を設定。
- 設定・環境読み込み（src/kabusys/config.py）
  - .env / .env.local 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - 複雑な .env パース機構を実装（export プレフィックス、クォート処理、インラインコメントの扱い等）。
  - Settings クラスを導入し、環境変数から各種設定（J-Quants / kabu API / DB パス / Paper Trading 設定 / 監視閾値 / 環境種別等）を取得可能に。
  - 必須環境変数未設定時は明示的なエラーを投げる _require() を実装。
  - PAPER_FILL_MODE 等の入力検証とデフォルトを実装。
- 実行用スクリプト
  - 監視ループ起動スクリプト (src/kabusys/run_monitoring.py)
    - SystemMonitor のポーリングループを起動するエントリポイントを実装。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - プロセス優先度を設定（utils.process_priority.set_process_priority を利用）。
    - stop_requested.flag による安全なシャットダウン検出。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を参照する仕様。
  - 実行エンジン起動スクリプト (src/kabusys/run_execution.py)
    - ExecutionEngine の起動エントリポイントを実装。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 DB（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を構築。
    - エンジンは別スレッドで実行し、stop_requested.flag による停止をサポート。実行 PID を data/execution.pid に記録する仕組み（pid_file を受け取る）。
- データベース・分析基盤
  - DuckDB および SQLite を利用したデータアクセスを考慮（複数モジュールで duckdb 接続を受け取る設計）。
  - 監視用テーブル初期化のため init_monitoring_db 呼び出しを配置（冪等に監視テーブル確保）。
- ポートフォリオ構築（src/kabusys/portfolio/*）
  - portfolio_builder.py
    - 銘柄選定（select_candidates）、等重み（calc_equal_weights）、スコア加重（calc_score_weights）を実装。
    - スコアが全て 0 の場合のフォールバックと警告。
  - risk_adjustment.py
    - セクター集中上限チェック（apply_sector_cap）を実装。既存ポジションと価格マップに基づいて候補除外。
    - レジームによる投下資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear のマッピングと未知レジームのフォールバック）。
  - position_sizing.py
    - allocation_method（risk_based / equal / score）に基づく株数算出ロジックを実装。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash を超える場合のスケーリングと端数配分）やコストバッファを考慮。
- リサーチ・特徴量（src/kabusys/research/*）
  - factor_research.py
    - Momentum / Volatility / Value ファクター計算実装（mom 1/3/6ヶ月、MA200 乖離、ATR20、20日平均売買代金、PER/ROE 等）。
    - DuckDB のウィンドウ関数を活用した高性能な集計実装。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、ファクター統計サマリ（factor_summary）、ランク関数（rank）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで統計量を算出。
  - research パッケージの __all__ に主要関数をエクスポート。
- AI ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news を集約して OpenAI（gpt-4o-mini）へ送信し、銘柄別センチメントスコアを ai_scores テーブルへ書き込む処理を実装。
  - ニュース集約ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を厳密に計算する calc_news_window。
  - バッチ処理（最大 20 銘柄/コール）、記事および文字数トリム、スコアクリッピング（±1.0）、レスポンス検証、エクスポネンシャルバックオフによるリトライ（429/ネットワーク/5xx 対応）を備えた堅牢な実装方針。
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() に依存しない設計。
- ツール（src/kabusys/tools/paper_verification_report.py）
  - Paper Trading の検証レポート生成ツールを実装。
  - system_status / trade_logs / risk_logs テーブルから稼働率、注文成功率・送信率、レイテンシ（avg/max/P95）等を集計し、閾値（稼働率 99% 等）に基づいて PASS/FAIL を出力。
  - コマンドライン引数 --from/--to/--db に対応。PAPER_TRADING_SQLITE_PATH 環境変数からの DB 指定も可能。
- ユーティリティ（src/kabusys/utils/process_priority.py）
  - set_process_priority(level) を実装し、Windows / POSIX（Linux, Darwin, FreeBSD）間の差分を吸収。
  - set_cpu_affinity(cpu_count) を実装（指定が None の場合は操作をスキップ）。
  - 権限不足や未対応環境時は警告を出し安全にスキップ。
- その他
  - パッケージ構成の整備（各モジュールの __init__ エクスポート整理）。
  - ドキュメントコメントと設計方針をモジュール内に多く追加し、可読性とメンテナンス性を向上。

Changed
- N/A（初回リリースのため変更履歴なし）

Fixed
- N/A（初回リリースのため修正履歴なし）

Security
- N/A

Notes / Migration
- 環境変数による挙動
  - 自動 .env 読み込みはデフォルトで有効。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - Paper Trading（KABUSYS_ENV=paper_trading）では専用の SQLite（PAPER_TRADING_SQLITE_PATH）を用いるため、本番 DB と完全に分離されます。
- デフォルトのファイルパス
  - duckdb: data/kabusys.duckdb
  - monitoring sqlite: data/monitoring.db
  - paper trading sqlite: data/paper_trading.db
  - PID / フラグ類: data/*.pid / data/*flag
- OpenAI API を用いる機能（ai.news_nlp）は API キーが必要です。api_key 引数か環境変数 OPENAI_API_KEY を設定してください。

--- 

開発や運用に関する不明点があれば、対象モジュール名を指定してさらに詳しく説明します。