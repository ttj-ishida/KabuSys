KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株自動売買システム「KabuSys」のコードベース（一部）です。  
ここに含まれるモジュール群は、戦略の研究／ファクター計算、ポートフォリオ構築、発注エンジン、監視・アラート、LLMを使ったニュース解析などの機能を提供します。

概要
----
KabuSys は以下の主要機能を備えたモジュール群で構成されています。

- 自動注文実行エンジン（ExecutionEngine）
- 監視サブシステム（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- 研究用モジュール（ファクター計算、特徴量探索、IC計算）
- AI（OpenAI）を用いたニュースセンチメント評価・市場レジーム判定
- 設定ウィザード (.env 作成) と設定検証ツール
- 各種ユーティリティ（プロセス優先度設定、レポート生成など）

特徴一覧
---------
- 設定は .env ファイルまたは環境変数で管理。config_setup で対話的に初期化可能。
- 実行環境の区別（development / paper_trading / live）をサポート。paper_trading モードは本番DBと完全分離して MockBroker を使用。
- 監視機能によりプロセス生存、データ鮮度、注文滞留、約定異常、ドローダウンなどを検知してログ / リスクテーブルに記録。条件により kill.flag を書き込んでエンジン停止を指示。
- DuckDB / SQLite を使ったデータ格納・分析基盤（prices_daily, raw_financials, ai_scores 等を前提）。
- OpenAI（gpt-4o-mini）を使ったニューススコアリング（ai.news_nlp）・レジーム判定（ai.regime_detector）。
- Paper Trading の挙動検証用レポート生成ツール。

前提条件（主な依存パッケージ）
---------------------------
実行には Python と以下パッケージが必要です（バージョンはプロジェクト側で管理してください）:

- Python 3.8+
- duckdb
- psutil
- openai (OpenAI Python SDK)
- PyYAML（config の YAML 検証を行う場合に必要）
- （標準ライブラリ: sqlite3 等を使用）

requirements.txt が用意されていない場合は上記パッケージをインストールしてください。

セットアップ手順
----------------

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML

4. .env の初期作成（対話ウィザード）
   - python -m kabusys.config_setup
     - ウィザードで J-Quants トークン、kabu API パスワード、DBパス、KABUSYS_ENV などを設定します。
     - .env は絶対に Git にコミットしないでください。

5. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合: python -m kabusys.validate_config --strict

6. （必要に応じて）DuckDB / SQLite のディレクトリ作成
   - デフォルトは data/ 以下に DB ファイルを置きます。親ディレクトリが存在しないと警告が出ますが、多くのモジュールが起動時に作成します。

主要な使い方（コマンド）
-----------------------

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を用い、paper_trading 用 DB（デフォルト data/paper_trading.db）に記録します。
  - 実行時に data/execution.pid へ PID を書き、停止は data/stop_requested.flag を作成するか KillSwitch の kill.flag（data/kill.flag）で制御します。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - デフォルトのポーリング間隔は 60 秒。環境変数で上書き可能:
    - MONITOR_POLL_INTERVAL=30  python -m kabusys.run_monitoring
  - 監視は実行環境にかかわらず本番用の sqlite_path を使用してログを残します（Settings.sqlit e_path）。

- 環境設定ウィザード（.env 作成/更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数:
    - PAPER_TRADING_SQLITE_PATH を使って DB を指定可能（デフォルト data/paper_trading.db）

停止・Kill 操作
----------------
- run_execution / run_monitoring は data/stop_requested.flag の存在をチェックし、あればループを終了します（手動停止用ファイル）。このファイルはプロジェクトルートの data/stop_requested.flag を想定しています。
- KillSwitch は Settings.kill_flag_path（デフォルト data/kill.flag）を作成して ExecutionEngine を停止させます。kill.flag は存在すれば再書き込みせず冪等に動作します。起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動でクリアする挙動になります（本番では推奨されません）。

主要な設定項目（環境変数）
-------------------------
（主なものを抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (アラート通知用、任意)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- KILL_FLAG_CLEAR_ON_START (0|1) — 起動時に kill.flag を自動クリアするか（0 推奨）

各モジュールの振る舞いメモ
-------------------------
- run_execution:
  - KABUSYS_ENV=paper_trading なら MockBrokerClient を使用、paper_trading 用 SQLite に記録。
  - 実行は別スレッドでエンジンを動作させ、stop flag を検知して安全に停止します。

- run_monitoring:
  - SystemMonitor.check_once を定期実行し、system_status/risk_logs/trade_logs 等へ記録します。
  - MONITOR_POLL_INTERVAL でポーリング間隔を指定可能（デフォルト 60 秒）。

- ai.news_nlp:
  - raw_news と news_symbols を集約して OpenAI に問い合わせ、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込みます。
  - API キーは OPENAI_API_KEY 環境変数または関数引数で与えます。API障害時はフォールバック・リトライを行います。

- ai.regime_detector:
  - ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して market_regime テーブルへ判定結果を書き込みます。

- monitoring.monitoring_db:
  - シンプルな SQLite 永続化層。テーブル初期化（マイグレーション含む）を行います。

ディレクトリ構成（抜粋）
-----------------------
以下は主要ソース配置のサンプル（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env のロードと Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py   — ペーパートレード検証レポート
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (未掲示箇所あり)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - process_priority.py
  - execution/                 — 発注関連コンポーネント（OrderManager 等。今回の抜粋に一部あり）
  - data/                      — デフォルト DB・フラグファイル置き場（運用時に生成）

運用上の注意
-------------
- .env を絶対にリポジトリへコミットしないでください（シークレット含む）。
- 本番環境（KABUSYS_ENV=live）では kill.flag の自動クリアを避ける（KILL_FLAG_CLEAR_ON_START=0 推奨）。
- OpenAI API キーは適切に管理してください。API 呼び出しはコストとレイテンシに留意すること。
- monitoring は本番 sqlite_path を参照して監視ログを残します。paper_trading 時は発注 DB を分離して運用されます。
- DuckDB / SQLite のファイル権限・バックアップを検討してください。

貢献・開発
-----------
- ローカル開発は KABUSYS_ENV=development を推奨。発注は行われません（実装方針に基づく）。
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使い .env 自動ロードを抑止できます。
- モジュールごとにユニットテストを追加して品質を担保してください（今回の抜粋にはテストは含まれていません）。

参考コマンドまとめ
------------------
- .env ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ペーパー検証レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

その他
-----
本 README はリポジトリ内のソース（主に src/kabusys 以下）を元に作成しています。詳細な設計や仕様（例えば PortfolioConstruction.md、StrategyModel.md 等）は別ドキュメントに記載されている想定です。運用前に必ず設定検証と少量のドライランを行ってください。