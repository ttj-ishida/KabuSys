KabuSys
=======

バージョン: 0.1.0

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤です。シグナル生成・ポートフォリオ構築・発注エンジン、監視（Monitoring）、リスク管理、研究用ファンクション群、OpenAI を用いたニュース解析／レジーム判定などを備えています。開発／ペーパートレード／本番（live）の各モードを想定し、設定ファイル（.env）や各種 DB（DuckDB / SQLite）でデータを永続化します。

主な特徴
--------
- ExecutionEngine: 発注フロー（本番は実ブローカー、paper_trading は MockBroker を使用）
- Monitoring: システム状態・注文・リスク監視、Kill Switch による緊急停止
- Portfolio: 候補選定、重み計算、ポジションサイジング、セクターキャップ等の純関数群
- Research: DuckDB ベースのファクター計算、将来リターン・IC 計算、統計サマリー
- AI モジュール: ニュースの NLP スコアリング（OpenAI）、市場レジーム判定
- ツール: ペーパートレード検証レポート生成スクリプト
- 設定支援: 対話式 .env 作成ウィザード（config_setup）、起動前チェック（validate_config）
- ロギング: 統一的なログ設定（コンソール + 日次ローテートファイル）

要件（主な依存）
----------------
以下は代表的な依存パッケージです（プロジェクトの requirements を参照してください）:
- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config/*.yaml を検証する場合）
その他、環境に応じて追加の依存があります。

セットアップ手順
--------------
1. リポジトリをクローン／配置し、仮想環境を作成して有効化します。
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate

2. 依存パッケージをインストールします（プロジェクトに requirements.txt がある場合はそちらを使用）。
   - pip install duckdb psutil openai PyYAML

3. .env の初期作成（対話式ウィザード）
   - python -m kabusys.config_setup
     - 対話に従って J-Quants トークン、kabuAPI パスワード、DB パス、環境（KABUSYS_ENV）などを設定します。
   - 生成された .env は絶対に Git にコミットしないでください。

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
     - 問題があればエラー／警告が表示されます。
     - --strict をつけると警告も失敗扱いになります。

5. DB やログ用ディレクトリの確認
   - デフォルトの DB/ログパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - ログ: logs/
   - 必要に応じて .env で DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / LOG_DIR を上書きできます。

主要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
- OPENAI_API_KEY: OpenAI を利用する機能で必要
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- LOG_LEVEL (デフォルト: INFO)
- LOG_DIR (デフォルト: logs/)
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 本番での Kill Flag 自動クリア（0 推奨）

使い方（主要コマンド）
---------------------

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV に依存:
    - paper_trading: MockBroker を使用し、DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に分離
    - live / development: 通常の設定に従う
  - 起動時に data/stop_requested.flag が存在すると起動しません。
  - エンジンは data/execution.pid を書きます（設定で変更可）。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
  - 監視は Settings.sqlite_path（監視 DB）を常に本番用パスで使用します（KABUSYS_ENV に依らず）
  - 停止はプロジェクトルート/data/stop_requested.flag を作成することで行えます。

- .env 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - オプション --strict で警告も失敗扱い

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）

運用に関する注意
----------------
- Kill Switch / Stop フラグ:
  - kill.flag (Settings.kill_flag_path, デフォルト data/kill.flag): ExecutionEngine 停止のために監視側（KillSwitch）が書き込むファイル。存在すると ExecutionEngine は停止されます。
  - stop_requested.flag: run_monitoring/run_execution のループ停止チェック用（プロジェクト内 data/stop_requested.flag）。
  - 実行時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動でクリアしますが、本番では推奨されません。

- ログ:
  - ログは stdout と logs/<app_name>.log に日次ローテートで出力されます（logs ディレクトリが作成できない場合はファイル出力が無効化され、コンソールのみになります）。
  - ログレベルは LOG_LEVEL 環境変数や setup_logging 呼び出し時の引数で制御できます。

- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等でテーブルといくつかのマイグレーション（カラム追加）を行います。

- OpenAI/API:
  - news_nlp や regime_detector は OPENAI_API_KEY を要求します。API 呼び出しでのエラーはリトライ／フェイルセーフ処理が組み込まれていますが、キー未設定だと実行できません。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py (パッケージ定義, __version__ = "0.1.0")
- config.py — 環境変数 / .env 自動ロードと Settings クラス
- config_setup.py — 対話式 .env ウィザード
- validate_config.py — 起動前設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — Monitoring ポーリングループ起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュースの OpenAI を使ったセンチメントスコアリング
  - regime_detector.py — マクロ + ETF MA による市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite 永続化レイヤ
  - system_monitor.py, trade_monitor.py, risk_monitor.py — 各種モニタ
  - monitoring_engine.py — 各モニタを束ねるエンジン
  - kill_switch.py, alert_manager.py — Kill Switch / 通知（AlertManager はコード参照）
- execution/ (発注ロジック関連) — BrokerFactory, ExecutionEngine, OrderManager 等（詳細はコード参照）
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 株数計算、リスク制約、単元丸め
  - risk_adjustment.py — セクター制限／レジーム乗数
- research/
  - factor_research.py — Momentum/Value/Volatility 等のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計サマリー
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート出力
- utils/
  - logging_setup.py — 共通ログ設定
  - process_priority.py — プロセス優先度 / CPU affinity 設定
  - その他ユーティリティ群

開発者向けメモ
---------------
- 自動で .env をロードする仕組みがあります（プロジェクトルートの .env / .env.local）。自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB 接続は研究／AI モジュールが利用します。prices_daily / raw_financials / raw_news などのテーブルを前提とします。
- モジュールは可能な限り "ルックアヘッドバイアス" を避ける設計になっています（target_date 未満のデータのみ使用など）。
- ローカル開発では KABUSYS_ENV=development を使用すると発注などの副作用を抑えられます。ペーパートレードは paper_trading を利用してください。

ライセンス / コントリビューション
---------------------------------
（この README にライセンス情報は含まれていません。必要に応じて LICENSE を追加してください）

サポート
--------
不具合・質問がある場合はコードの該当ファイル（例: run_execution.py, monitoring/*.py）を参照の上、Issue を作成してください。

以上。