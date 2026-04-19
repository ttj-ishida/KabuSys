README
=====

概要
----
KabuSys は日本株向けの自動売買・研究基盤です。  
主な目的はアルゴリズムで売買シグナルを生成し、発注・約定管理、稼働監視、ペーパートレード検証、ファクター研究、ニュース NLP による補助情報などを統合することです。コードはモジュール化されており、ローカル開発（development）、ペーパートレード（paper_trading）、本番（live）を想定した設定で動作します。

主な特徴
--------
- ExecutionEngine（発注エンジン）
  - 本番 (live) とペーパートレード (paper_trading) を切り替え可能。paper_trading 時は MockBrokerClient を使い DB を分離。
- Monitoring（監視）
  - システム稼働監視、データ鮮度チェック、注文ログ監視、リスク（ドローダウン・ポジション数）監視、Kill Switch（停止フラグ）機能。
- Portfolio 構築ユーティリティ
  - 候補選定、等配分／スコア配分、リスク調整（セクター制限・レジーム乗数）、ポジションサイズ計算（単元丸め・集約上限）。
- Research（研究）モジュール
  - モメンタム・バリュー・ボラティリティ等のファクター算出、将来リターン計算、IC（情報係数）計算、統計要約。
- AI 統合
  - ニュースのセンチメントスコアリング（OpenAI API）と市場レジーム判定（MA200 + マクロセンチメント）。
- ユーティリティ
  - ログ設定、プロセス優先度／CPU affinity 設定、設定ウィザード・検証 CLI、ペーパートレード検証レポート生成ツール。

必要要件
--------
推奨 Python 3.9+。主要依存（抜粋）:
- duckdb
- psutil
- openai
- PyYAML（config ファイル検証時に必要）
- sqlite3（標準モジュール）

セットアップ手順
----------------
1. レポジトリをクローン
   - git clone ...

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate

3. 依存パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   - （requirements.txt がある場合は pip install -r requirements.txt を使用）

4. 初期 .env の作成（対話式ウィザード）
   - python -m kabusys.config_setup
     - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
     - KABUSYS_ENV は development / paper_trading / live のいずれか

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗として扱います（exit 1）。

主要な環境変数（抜粋）
---------------------
（.env は絶対にリポジトリにコミットしないでください）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development / paper_trading / live） デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 時）
- OPENAI_API_KEY: OpenAI 呼び出し用キー（AI 機能を使う場合）
- LOG_LEVEL / LOG_DIR: ログ出力設定
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring 用、デフォルト 60）

使い方（主要スクリプト）
-----------------------

1) 環境ウィザード（.env 作成）
   - python -m kabusys.config_setup

2) 設定検証
   - python -m kabusys.validate_config
   - 厳密モード: python -m kabusys.validate_config --strict

3) ExecutionEngine の起動（発注エンジン）
   - python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db にログを残します（本番 DB と分離）。
     - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
     - 起動中は data/execution.pid に PID を書きます（設定で変更可能）。
     - Kill Switch（data/kill.flag）が書かれると Engine 側で停止処理を行います（KillSwitch は監視側が書き込み）。

4) Monitoring の起動（監視ループ）
   - python -m kabusys.run_monitoring
   - 挙動:
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
     - Monitoring 自体は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用して監視データを永続化します（監視データは共有して追跡される想定）。
     - 監視で Kill Switch 判定が成立すると data/kill.flag を書いて ExecutionEngine を停止させることができます。
     - data/stop_requested.flag を置くと監視スクリプト自体を止めるためのフラグとして利用されます。

5) Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
   - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
   - レポートは稼働率、注文成功率、レイテンシ（P95）等を算出し PASS/FAIL を表示します。

設定ファイル・DB 初期化
-----------------------
- run_execution / run_monitoring は起動時に監視用テーブルの作成（init_monitoring_db）を行います（冪等）。  
- DuckDB や SQLite の既定パスは data/ 以下に置かれます。必要に応じて .env の DUCKDB_PATH / SQLITE_PATH を書き換えてください。
- .env 内 KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

停止・Kill フロー
------------------
- 監視（Monitoring）プロセスは重大リスク検出時に KillSwitch を評価して data/kill.flag を書くことがあります。ExecutionEngine はこのファイルの存在を見て安全に停止します。
- 監視プロセスやエンジン自体を外部から即時停止したい場合は data/stop_requested.flag を置くと run_* スクリプトがループを抜けて終了します。

ログ
----
- ログは標準出力と logs/<app_name>.log（日次ローテーション）に出力されます。ログレベルは LOG_LEVEL、ログディレクトリは LOG_DIR で制御可能です。

開発向けメモ
------------
- 設定の自動ロード: config.py はプロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動読み込みします。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- テストの容易さのため、OpenAI 呼び出し部分は内部で分離され、ユニットテスト時に _call_openai_api 等をモックできます。
- DuckDB を用いて research 周りの SQL + Python ハイブリッド実装でファクター計算を行います。prices_daily / raw_financials 等のテーブル設計に依存します。

ディレクトリ構成（要点）
--------------------
（ソースは src/kabusys 以下）

- src/kabusys/
  - __init__.py                — パッケージ定義、バージョン
  - config.py                  — 環境変数・設定読み込みロジック
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - execution/                 — 発注エンジン関連（Engine, OrderManager, RiskManager など）
  - monitoring/
    - monitoring_db.py         — 監視 DB 層（SQLite）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py               — ニュース NLP（OpenAI）
    - regime_detector.py       — レジーム判定（MA200 + マクロセンチメント）
  - utils/
    - logging_setup.py
    - process_priority.py

補足
----
- AI 機能（news_nlp, regime_detector）を利用するには OPENAI_API_KEY が必要です。API エラーやパース失敗は耐障害的に扱われる設計ですが、正しくキーをセットすることを推奨します。
- 本 README はコードベース内の docstring / コメントに基づく要約です。細かな使い方や追加設定は該当モジュールの docstring を参照してください。

以上。必要であればセクションの追記（例: 各モジュールの API 使用例や CI の説明）を行います。