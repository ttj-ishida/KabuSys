KabuSys
======

日本株向けの自動売買システムのモジュール群（ライブラリ＋実行スクリプト群）です。
このリポジトリには監視（Monitoring）、実行エンジン（Execution）、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）等の主要コンポーネントが含まれます。

プロジェクト概要
--------------
KabuSys は以下のような役割をもつ主要コンポーネントを備えたシステムです。

- ExecutionEngine：ブローカーへの発注・注文状態管理・リスク管理を行う実行エンジン（run_execution.py）。
- Monitoring：システム稼働状況 / 注文異常 / リスク監視を行うモニタリング（run_monitoring.py、MonitoringEngine、Streamlit ダッシュボード）。
- Portfolio：銘柄選定、重み付け、ポジションサイズ算出等のポートフォリオ構築ロジック。
- Research：ファクター計算や特徴量探索のユーティリティ（DuckDB を用いたデータ解析）。
- AI：ニュースの NLP スコアリング（OpenAI を利用）や市場レジーム判定。
- Tools：Paper Trading の検証レポート生成などのユーティリティスクリプト。

主な特徴（機能一覧）
-----------------
- 実行 / 監視プロセスの分離（監視は本番 DB を参照しつつ実行プロセスを監視）。
- Paper Trading モード（KABUSYS_ENV=paper_trading）では発注先をモック化し、専用の SQLite DB に分離。
- モニタリング：
  - システムリソース監視（CPU / メモリ / ディスク）
  - データ鮮度チェック（株価テーブルの最終日付チェック）
  - 注文滞留検出・約定価格異常検出
  - ドローダウン・ポジション上限監視と kill.flag による自動停止
  - LINE によるアラート通知（AlertManager）
  - Streamlit ダッシュボード（read-only モードで DB を可視化）
- Portfolio：スコア・等分配・リスクベースの配分、セクターキャップ、レジーム乗数
- Research：モメンタム・ボラティリティ・バリュー等のファクター計算、IC 計測、統計サマリ
- AI：ニュースを LLM に送って銘柄ごとのセンチメントを ai_scores に格納、マクロニュース＋ETF マクロを合成したレジーム判定
- ユーティリティ：Paper Trading 検証レポート生成ツール

セットアップ手順
----------------

前提
- Python 3.10 以上（Union 型記法などに対応していること）
- システム依存パッケージ（psutil など）
- DuckDB、requests、openai、streamlit 等の Python パッケージ

1. 仮想環境を作る（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   （プロジェクトに requirements.txt があれば pip install -r requirements.txt を利用してください）

3. プロジェクトルートの data ディレクトリを作成
   - mkdir -p data

4. 環境変数の設定
   - プロジェクトルートに .env（または .env.local）を置くと自動で読み込まれます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主要な環境変数（後述の「環境変数」節を参照）を設定してください。

5. DB 初期化
   - run_monitoring.py や run_execution.py は起動時に monitoring DB のテーブルが存在することを保証する初期化を行います（init_monitoring_db）。
   - data データファイル（data/monitoring.db, data/paper_trading.db, data/kabusys.duckdb 等）は起動時に自動作成されます（ただし DuckDB 用のテーブルは別途パイプラインでロードする必要があります）。

環境変数（主なもの）
--------------------
※値はデフォルトや有効値を明示しています。必要に応じ .env に定義してください。

- KABUSYS_ENV: 起動環境
  - 有効値: development | paper_trading | live
  - デフォルト: development

- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API 用のトークン
- KABU_API_PASSWORD: （必須）kabuステーション API のパスワード
- OPENAI_API_KEY: OpenAI を使う機能 (news_nlp / regime_detector) の API キー

- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring）DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の約定挙動
  - 有効値: instant | partial | never | reject
  - デフォルト: instant

- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: Kill switch の flag パス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring.py で上書き可能。default=60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

運用上のフラグファイル
- data/stop_requested.flag: run_monitoring / run_execution 停止用の外部フラグ（存在するとループを抜けます）
- data/kill.flag: KillSwitch が書き込む停止フラグ（ExecutionEngine に停止シグナル）

使い方
------

基本的な実行例（プロジェクトをパッケージとして実行する場合）
- 監視プロセス起動（SystemMonitor ベースのポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL を環境変数で秒数指定可能（例: MONITOR_POLL_INTERVAL=30）

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用の DB（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と分離）。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - もしくは引数 --db で監視用 DB を指定可能。read-only URI で開くため実稼働 DB を直接破壊しません。

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数を上書き）

運用上の注意
- Monitoring は Settings にかかわらず sqlite_path（監視 DB）を参照します。監視ログは常に指定の monitoring DB に書き込まれます。
- ExecutionEngine は KABUSYS_ENV により DB を切り替えます（paper_trading の場合は paper_sqlite_path を使用）。
- kill.flag の作成は KillSwitch により行われます。ExecutionEngine は起動時に kill.flag が既にある場合は起動をスキップします（安全装置）。
- 実行時のプロセス優先度を set_process_priority("high") で試みます。権限によって失敗することがありますが、ログに記録されるだけで致命的ではありません。
- OpenAI を使う機能 (news_nlp.score_news / regime_detector.score_regime) を利用するには OPENAI_API_KEY が必要です。API の失敗時はフェイルセーフで処理を継続する実装が組み込まれています（ゼロにフォールバック等）。

ディレクトリ構成
----------------
以下は src/kabusys 以下の主要なファイル・モジュールの概観です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数読み込み・Settings クラス（.env 自動ロード等）
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート生成ツール
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP スコアリング（OpenAI 経由）
    - regime_detector.py            — 市場レジーム判定（ETF + マクロ NLP）
  - monitoring/
    - __init__.py
    - monitoring_db.py              — SQLite 監視 DB 層（テーブル作成・読み書き）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他発注関連モジュール: broker_factory 等)
  - portfolio/
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - process_priority.py
    - __init__.py
  - data/                            — 実行時に使用するデータディレクトリ（DB・PID・フラグ等）

追加情報（開発・デバッグ）
-----------------------
- .env 自動ロード
  - config.py はプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を走査して .env / .env.local を自動読み込みします。
  - OSの環境変数が優先されます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- ログ
  - 各モジュールは logging を利用しています。LOG_LEVEL を環境変数で設定できます（デフォルト INFO）。

- テスト用の差し替え
  - AI の外部呼び出しはユニットテストで差し替え可能な設計（内部の _call_openai_api を patch）になっています。

よく使うコマンドまとめ
--------------------
- 監視開始:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン開始:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

ライセンス・貢献
----------------
（本 README のサンプルにはライセンス・貢献ガイドラインは含まれていません。必要に応じて追加してください。）

以上。プロジェクトの各モジュールに関する詳しい実装コメント・ドキュメントは各ソースファイルの docstring／コメントを参照してください。エンドツーエンドの立ち上げや DuckDB へのデータ投入パイプラインについては別途データ準備手順を用意することを推奨します。