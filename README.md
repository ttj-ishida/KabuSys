KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株の自動売買・研究・監視を行うためのモジュール群です。  
本リポジトリは注文実行 (ExecutionEngine)、監視 (Monitoring)、ポートフォリオ構築、ファクター計算、AI を用いたニュースセンチメント評価などの機能を提供します。  
設計方針としては「本番 DB とペーパートレード DB の分離」「ルックアヘッドバイアス回避」「外部呼び出し（API）は明示的に行う」「フェイルセーフ（API失敗時のフォールバック）」を重視しています。

主な機能
-------
- Execution
  - 実際のブローカー / モックブローカーを用いた発注エンジン（KABUSYS_ENV による切替）
  - リスク管理（ポジション上限・最大ドローダウン等）
  - 発注ログの永続化（SQLite）
- Monitoring
  - システムリソース（CPU/メモリ/ディスク）・プロセス稼働監視
  - 注文ログ監視（滞留注文、約定異常など）
  - リスク監視（ドローダウン・ポジション数）
  - Kill Switch（条件を満たした場合に kill.flag を書き込み、Execution を停止）
  - 監視結果の永続化（SQLite）およびアラート通知フック
- Portfolio / PortfolioConstruction
  - 候補選定、等金額・スコア加重配分、ポジションサイズ計算
  - セクター上限・レジーム乗数の適用
- Research
  - DuckDB を用いたファクター計算（Momentum, Volatility, Value 等）
  - 将来リターン計算、IC 計算、ファクター統計
- AI
  - ニュース NLP（OpenAI を用いた銘柄別センチメントスコア生成）
  - レジーム判定（ETF の MA とマクロニュースの LLM センチメントを合成）
- ツール
  - .env 対話式ウィザード（config_setup）
  - 設定検証ツール（validate_config）
  - Paper Trading 検証レポート生成スクリプト

環境変数（主要）
----------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

運用に関係する主要変数:
- KABUSYS_ENV: execution モードを切替（development / paper_trading / live）
  - paper_trading: MockBroker を使い data/paper_trading.db に記録（本番 DB とは分離）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で使用）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレード時の注文埋め方（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1 でクリア）
- LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）

.note: 本ライブラリは起動時にプロジェクトルートの .env/.env.local を自動で読み込みます（無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

セットアップ
----------
1. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - 必須（例）:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（validate_config で YAML 検証を行いたい場合）
   - 具体的には requirements.txt がある場合は:
     - pip install -r requirements.txt

3. .env の準備
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは手動で .env を作成 (リポジトリの .env.example を参考に)

4. 設定検証（起動前に実行推奨）
   - python -m kabusys.validate_config
   - 警告も厳格に扱う場合: python -m kabusys.validate_config --strict

5. データ / ログ ディレクトリ作成（必要に応じて）
   - data/, logs/ は自動作成されますが、権限等が問題で作成に失敗する場合は手動で作成してください。

基本的な使い方
------------
- 実行エンジン起動（ExecutionEngine）
  - 本番/ペーパートレードは KABUSYS_ENV に依存:
    - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し data/paper_trading.db に記録します。
  - コマンド:
    - python -m kabusys.run_execution
  - 停止方法:
    - data/stop_requested.flag を作成すると起動中の run_execution は検出して終了します。
    - kill.flag は ExecutionEngine に停止指示を与えるための別のフラグ（monitoring 側が書き込む）。

- 監視プロセス起動（Monitoring）
  - コマンド:
    - python -m kabusys.run_monitoring
  - ポーリング間隔:
    - 環境変数 MONITOR_POLL_INTERVAL で秒数を上書き（デフォルト 60）
  - 監視は常に（KABUSYS_ENV に関わらず）本番 sqlite_path を参照して監視データを書き込みます（監視 DB は共有の monitoring.db を使う設計）。

- Paper Trading 検証レポート
  - コマンド:
    - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定:
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数が未設定の場合）

- AI 関連
  - OpenAI を使う機能（news_nlp, regime_detector）は OPENAI_API_KEY が必要。
  - API 呼び出しはリトライ・バックオフ・バリデーションを備えた実装です。

運用に関する注意
----------------
- 本番環境では KABUSYS_ENV=live を指定し、LINE の通知設定（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）を適切に構成してください。
- KILL_FLAG_CLEAR_ON_START=1 は本番で危険です（自動的に kill.flag をクリアしてしまうため、デフォルト 0 を推奨）。
- run_execution は起動時に pid ファイル（data/execution.pid など）を書きます。プロセス優先度を "high" に設定する処理を行いますが、権限によっては設定に失敗する場合があります（警告ログ）。
- DuckDB / SQLite に対する互換性や executemany の空リスト挙動など、コメントにあるバージョン依存の注意点があります。

ディレクトリ構成（抜粋）
---------------------
src/ (パッケージルート)
- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 起動前チェック CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリング起動スクリプト
  - execution/
    - （注文実行に関する各種クラス: broker_factory, execution_engine, order_manager, order_repository, reconciler, risk_manager 等）
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層
    - system_monitor.py       — システム / データ鮮度監視
    - trade_monitor.py        — 注文ログ監視（存在）
    - risk_monitor.py         — ドローダウン・ポジション上限チェック
    - kill_switch.py          — kill.flag の管理
    - monitoring_engine.py    — 各 Monitor の統合ポーリング
    - alert_manager.py        — （存在するならアラート送信管理）
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み付け
    - position_sizing.py      — 株数決定・資金スケール
    - risk_adjustment.py      — セクター制限・レジーム乗数
  - research/
    - factor_research.py      — Momentum/Value/Volatility 等の計算（DuckDB）
    - feature_exploration.py  — 将来リターン・IC・統計
  - ai/
    - news_nlp.py             — ニュースセンチメント（OpenAI）
    - regime_detector.py      — 市場レジーム判定（MA + マクロ NLP）
  - data/                    — 実行時データ（data/kabusys.duckdb, data/monitoring.db 等）
  - logs/                    — ログファイル（logs/<app_name>.log）
  - tools/
    - paper_verification_report.py

ログとデータ
------------
- デフォルトのログディレクトリ: logs/
  - run_execution なら logs/execution.log、run_monitoring なら logs/monitoring.log
- デフォルトのデータディレクトリ: data/
  - data/kabusys.duckdb（DuckDB）
  - data/monitoring.db（監視用 SQLite）
  - data/paper_trading.db（PAPER_TRADING 用）
  - data/kill.flag（Kill Switch）
  - data/stop_requested.flag（手動停止リクエスト）
  - data/execution.pid（ExecutionEngine の pid）

開発者向け補足
--------------
- 自動で .env をロードする実装があります（config.py）。テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- validate_config は PyYAML がインストールされていない場合、YAML 検証をスキップします（警告を出します）。
- AI 周りのユーティリティは OpenAI の SDK に依存しており、API レスポンスのバリデーション・リトライを実装済みです。テストでは API 呼び出し部分をモックすることを想定しています。

よくあるコマンド一覧
-------------------
- .env を作成（ウィザード）:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視プロセス起動:
  - python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス・貢献
----------------
（この README にはライセンス情報やコントリビュート手順は含まれていません。リポジトリの LICENSE / CONTRIBUTING ファイルを参照してください。）

フィードバック・問題報告
-----------------------
バグ報告や改善提案は Issue を作成してください。実運用に関する重要な変更（特に KILL/STOP 挙動・DB スキーマ）は慎重にレビューしてください。

以上。必要であれば README にサンプル .env（項目例）やシーケンス図、さらに詳細な運用手順（デプロイ、systemd サービス定義例、監視アラート送信先設定例）を追加できます。どの情報を追記しますか？