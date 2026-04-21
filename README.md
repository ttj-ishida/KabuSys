README
======

概要
----
KabuSys は日本株向けの自動売買システム向けユーティリティ群です。本リポジトリには、発注エンジン起動スクリプト、監視（Monitoring）コンポーネント、ポートフォリオ構築／サイズ計算、研究用ファクター計算、AI を使ったニュースセンチメント評価などのモジュール群が含まれます。設計方針として「本番データベースや発注 API に不要にアクセスしない」「ルックアヘッド（未来参照）を避ける」「フェイルセーフな挙動」を重視しています。

主な特徴
--------
- 起動スクリプト
  - run_execution: ExecutionEngine（発注エンジン）を起動
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、paper_trading 用 DB に記録して本番 DB と分離
  - run_monitoring: SystemMonitor のポーリングループを起動（デフォルト 60 秒）
- 設定管理
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: .env と config/*.yaml の検証 CLI（--strict 指定で警告も失敗扱い）
  - Settings クラス: 環境変数アクセスラッパ
- 監視系
  - monitoring_engine: System/Trade/Risk Monitor を束ねるポーリングエンジン
  - monitoring_db: SQLite ベースの永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
  - KillSwitch: フラグファイルにより ExecutionEngine を停止させる仕組み
- 発注／リスク
  - OrderManager / RiskManager / ExecutionEngine など（発注ロジックは execution パッケージに分離）
- ポートフォリオ構築（純粋関数群）
  - 銘柄選定、等重・スコア重み、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイズ計算
- 研究・分析
  - research パッケージ: ファクター計算（モメンタム、ボラティリティ、バリュー）、IC 計算、特徴量サマリー
  - DuckDB を使ったデータ処理（prices_daily / raw_financials 等を想定）
- AI（OpenAI）連携
  - ai.news_nlp: ニュースを LLM に投げて銘柄別センチメントを算出・ai_scores に書き込み
  - ai.regime_detector: ETF（1321）MA200 乖離 + マクロ記事センチメントから市場レジーム判定
  - API 呼び出しはリトライ・JSON バリデーション・スコアクリッピングなどを備える
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成（成功率・レイテンシ・稼働率など）

前提・必須環境
--------------
- Python 3.9+
- 必要ライブラリ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証をフルに行う場合）
- その他ツールは任意（sqlite3 は標準ライブラリで利用）

（実際の requirements.txt はプロジェクトに合わせて用意してください。最低限次のパッケージが必要です）
pip install duckdb psutil openai PyYAML

環境変数と .env
----------------
主要な必須環境変数
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- OPENAI_API_KEY（AI 機能を使う場合必須）
その他
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBroker を使用して data/paper_trading.db に記録
  - live: 実際の発注が行われます（注意）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL / LOG_DIR
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか、開発用途）

.env は config_setup.py のウィザードで対話的に生成できます:
python -m kabusys.config_setup

設定検証は validate_config で実行:
python -m kabusys.validate_config
厳密モード:
python -m kabusys.validate_config --strict

セットアップ手順
----------------
1. リポジトリをチェックアウト
2. Python 仮想環境を用意し有効化
   python -m venv .venv
   source .venv/bin/activate  # Unix
3. 必要パッケージをインストール
   pip install duckdb psutil openai PyYAML
   （プロジェクトに requirements.txt があれば pip install -r requirements.txt）
4. .env の初期作成
   python -m kabusys.config_setup
   -> ウィザードに従って値を入力し .env を作成
5. 設定検証
   python -m kabusys.validate_config
   （問題がなければ OK が表示されます）
6. データディレクトリ作成（必要なら）
   mkdir -p data logs

基本的な使い方
--------------
- ExecutionEngine（発注エンジン）起動
  - 通常（環境変数で制御）
    KABUSYS_ENV=development python -m kabusys.run_execution
  - Paper Trading（モックブローカー、data/paper_trading.db に書き込み）
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 注意: run_execution は起動時に PID ファイル（data/execution.pid）を利用し、data/stop_requested.flag が存在すると起動しません

- Monitoring（監視ループ）起動
  python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60）
  - 監視は実行環境に関係なく本番 sqlite_path を使用します（監視は本番 DB を参照する設計）

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report
  期間指定:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  DB 指定:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI 系機能
  - ニューススコアリング（コード例）
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="...")

  - レジーム判定
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")

  いずれも OPENAI_API_KEY が必要（引数で渡すか環境変数で指定）

実行時のログ
-------------
- ログは logs/<app_name>.log に日次ローテーションで出力されます（デフォルト logs ディレクトリ）
- app_name 例: execution, monitoring
- LOG_LEVEL および LOG_DIR 環境変数で調整可能

運用・停止
----------
- Kill Switch:
  - kabusys.monitoring.kill_switch が条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります
  - Settings.kill_flag_clear_on_start が 1 の場合は起動時に自動で kill.flag をクリアします（本番では 0 を推奨）
- 強制停止（監視/実行スレッド）
  - run_monitoring と run_execution は stop flag（data/stop_requested.flag）や KeyboardInterrupt（Ctrl+C）で終了します

ディレクトリ構成（主要ファイル）
------------------------------
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み・Settings クラス
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - monitoring/
    - monitoring_db.py       — SQLite テーブル作成／読み書き
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （注文系の監視コード）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 管理
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - alert_manager.py       — 通知管理（LINE など）
  - execution/                — 発注関連（BrokerFactory, ExecutionEngine, OrderManager, Reconciler, RiskManager 等）
  - portfolio/
    - portfolio_builder.py    — 候補選定・等重／スコア重み
    - position_sizing.py      — 株数決定・aggregate cap 等
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - data/                     — データ処理パイプライン・DuckDB 接続（prices_daily 等）
  - research/
    - factor_research.py      — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py  — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — 市場レジーム判定
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
    - ... その他ユーティリティ

注意事項 / 運用上のガイド
------------------------
- 本番環境（KABUSYS_ENV=live）では必ず設定を再確認してください。validate_config は live 特有の警告もチェックします。
- .env は機密情報を含みます。絶対に Git にコミットしないでください（config_setup も同旨を出力します）。
- OpenAI API を使う機能は API コストとレイテンシの観点で運用設計が必要です。API キーは安全に管理してください。
- Paper Trading モードは本番 DB と分離されていますが、起動時のパスや環境変数を誤ると実 DB に影響する可能性があるため注意してください。
- Process priority / CPU affinity の変更処理は権限や OS により失敗することがあります（ログで警告を確認してください）。

開発者向けメモ
----------------
- 単体関数（portfolio や research）の多くは純粋関数で DB 参照を持たないためユニットテストが容易です。
- monitoring_db.init_monitoring_db はスキーマ追加（マイグレーション）を簡易的に行います。既存 DB からの互換性を考慮した処理が含まれます。
- OpenAI 呼び出しはテスト時に patch しやすいように _call_openai_api を分離しています。

問い合わせ・貢献
----------------
バグ報告・機能提案・プルリクエストはリポジトリの Issue / PR を利用してください。README にない実行例や追加ドキュメントが必要であれば Issue を立ててください。

以上。必要なら README に追記したい項目（例: より詳しい起動例、requirements.txt、docker-compose サンプル等）を教えてください。