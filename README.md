KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買・監視・研究ユーティリティ群を含む Python パッケージ（kabusys）です。  
README ではプロジェクト概要、主な機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめます。

プロジェクト概要
----------------
KabuSys は以下の主要コンポーネントを持つ自動売買補助ライブラリです。

- 実行エンジン（ExecutionEngine）起動スクリプト（run_execution）  
  - 本番 / ペーパートレードを切り替え可能。ペーパートレード時は MockBrokerClient を使い DB を分離。
- 監視コンポーネント（Monitoring）起動スクリプト（run_monitoring）  
  - システム状態、データ鮮度、注文・ポジション・リスクの監視。Kill Switch による強制停止書き込みをサポート。
- ポートフォリオ構築（portfolio）モジュール  
  - 候補選定、重み計算、ポジションサイズ算出、セクター制約、レジーム乗数など。
- 研究（research）モジュール  
  - ファクター計算（モメンタム、バリュー、ボラティリティ）、特徴量探索、IC 計算等（DuckDB 接続を用いる）。
- AI 補助（ai）モジュール  
  - ニュース NLP による銘柄センチメント評価（OpenAI を使用）、市場レジーム判定ロジック等。
- ユーティリティ（utils）  
  - ロギング設定、プロセス優先度／CPU affinity 設定、設定読み込みなど。
- 管理ツール（config_setup, validate_config, tools）  
  - .env の対話式作成、設定検証、Paper Trading 検証レポート生成など。
- 永続化（monitoring_db）  
  - 監視用 SQLite スキーマ定義と永続化 API。

主な機能一覧
--------------
- 設定管理:
  - .env 自動読み込み（プロジェクトルートの .env, .env.local）
  - 対話式ウィザード（python -m kabusys.config_setup）
  - 設定検証ツール（python -m kabusys.validate_config）
- 実行/監視:
  - run_execution: ExecutionEngine を起動（本番 / ペーパー切替）
  - run_monitoring: SystemMonitor を定期実行（ポーリング間隔は環境変数で変更可）
  - Kill Switch（data/kill.flag）で ExecutionEngine を安全停止
  - stop フラグ（data/stop_requested.flag）で run_* スクリプトを優雅に終了
- 監視 DB（SQLite）:
  - system_status, trade_logs, positions, risk_logs, dashboard を管理
- ポートフォリオ構築:
  - 候補選定 / 等配分・スコア配分 / リスクベース割当 / 単元株丸め / セクター制約
- 研究:
  - DuckDB を使ったファクター計算（mom, value, volatility）や IC 計算
- AI:
  - OpenAI を用いたニュースセンチメント集計（batch + JSON モード・リトライ実装）
- レポート:
  - Paper Trading の検証レポート生成（tools/paper_verification_report.py）

セットアップ手順
----------------
1. 必要な Python バージョン
   - Python 3.9+ を推奨（コードは型注釈で 3.9+ 機能を利用）

2. 必須パッケージ（最低限）
   - duckdb
   - psutil
   - openai
   - （オプション）PyYAML（validate_config で config/*.yaml を検証する場合）

   例:
   - pip を使う場合:
     pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt が無い場合は上記を手動でインストールしてください）

3. プロジェクトルートに移動し、.env を作成
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - 手動で作る場合は .env.example を参考にしてください（リポジトリ内に例がある想定）。

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗として扱います。

5. データディレクトリ
   - デフォルトの DB / ファイルパスは data/ 以下（例: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db）
   - 必要なら環境変数で上書き（下記参照）

主な環境変数（抜粋）
--------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBrokerClient を使用し data/paper_trading.db を使用
  - live: 本番ブローカーを使用
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- OPENAI_API_KEY（AI 機能を利用する場合）
- PAPER_FILL_MODE（paper_trading の約定挙動: instant | partial | never | reject）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒）、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（Execution 起動時に kill.flag を自動クリアするか、"1" でクリア）

基本的な使い方
----------------

1. .env の作成（対話式）
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - 問題がなければ OK 表示されます

3. 実行エンジンの起動（ローカル実行）
   - 本番 / ペーパートレード切替は KABUSYS_ENV で制御
   - 例（ペーパートレード）:
     KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   - 例（本番）:
     KABUSYS_ENV=live python -m kabusys.run_execution

   特記事項:
   - ペーパートレードでは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
   - run_execution は data/stop_requested.flag を検知するとエンジンを停止します。PID ファイル（data/execution.pid）を出力します。

4. 監視ループの起動
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数で秒単位のポーリング間隔を上書きできます（例: MONITOR_POLL_INTERVAL=30）。
   - 監視は monitoring DB（SQLite）に system_status, trade_logs, positions, risk_logs, dashboard を永続化します。
   - stop を要求するにはプロジェクトルートの data/stop_requested.flag ファイルを作成（監視ループは検知次第停止します）。

5. Kill Switch（Execution の強制停止）
   - KillSwitch は監視で条件を満たした場合に data/kill.flag を書き込みます（ExecutionEngine はこれを検知して安全停止します）。
   - 本番では KILL_FLAG_CLEAR_ON_START=0 を推奨（誤ってクリアしないため）。

6. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - --db で別 DB を指定できます。環境変数 PAPER_TRADING_SQLITE_PATH でも指定可。

7. AI スコアリング（ニュース）
   - プログラム的に呼び出す例:
     from kabusys.ai.news_nlp import score_news
     import duckdb, datetime
     conn = duckdb.connect("data/kabusys.duckdb")
     score_news(conn, target_date=datetime.date(2026,4,11), api_key="sk-...")

   - 注意: OpenAI API キーが必要。API 呼び出しはリトライと JSON バリデーションを実装済み。

ログと監査
-----------
- ログはデフォルトで logs/ ディレクトリに app_name ごとに日次ローテートで保存されます（kabusys.utils.logging_setup）。
- コンソール出力は stdout を用います。
- LOG_LEVEL で詳細度を制御できます。

停止／再起動、フラグ類
----------------------
- 停止要求:
  - data/stop_requested.flag を作ると run_monitoring / run_execution のループが終了します（監視側は検知して処理を停止）。
- Kill Switch:
  - data/kill.flag に理由テキストを書き込み、ExecutionEngine はこれを検出して停止します。KillSwitch は一度書いたら上書きしません（冪等）。
- PID ファイル:
  - run_execution は data/execution.pid に PID を書きます（Engine の管理用）。

主要なモジュール説明（簡易）
--------------------------
- kabusys.config
  - 環境変数読み込み・検証。プロジェクトルートの .env を自動読み込み（無効化可能）。
- kabusys.run_execution
  - ExecutionEngine の起動ラッパー。paper_trading 時は専用 DB を使用。
- kabusys.run_monitoring
  - SystemMonitor を定期実行する起動ラッパー。
- kabusys.monitoring.*
  - MonitoringDB、SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、MonitoringEngine 等（監視用ロジック）。
- kabusys.portfolio.*
  - ポートフォリオ構築（候補選定、重み、ポジションサイズ、セクター制約、レジーム乗数）。
- kabusys.research.*
  - DuckDB を用いたファクター計算、IC、統計サマリー等。
- kabusys.ai.*
  - ニュース NLP（news_nlp）、市場レジーム判定（regime_detector）。
- kabusys.tools.paper_verification_report
  - Paper Trading のパフォーマンス／健全性レポート生成。

ディレクトリ構成
-----------------
（リポジトリの src/kabusys 配下の主要ファイル・フォルダ例）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py (参照実装がある想定)
    - execution/
      - execution_engine.py (主要エンジン本体)
      - broker_factory.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - monitoring/ （上記）
    - tools/
      - paper_verification_report.py
      - __init__.py
    - data/ (実行時に使用される: DB・フラグ・PID 等)
    - logs/ (ログ格納場所、デフォルト)

補足・運用上の注意
------------------
- 本番環境（KABUSYS_ENV=live）ではすべての設定（API トークン、LINE 通知など）を厳密に確認してください。validate_config は live の注意点もチェックします。
- kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START）は本番では無効（0）にすることを推奨します。
- OpenAI API を利用する機能はネットワーク依存・API コストがかかるため運用ルールを設けてください（レート制限・エラーハンドリングは実装済み）。
- DuckDB / SQLite ファイルはバックアップを検討してください。特に paper_trading DB は操作・検証に利用されます。

開発者向け
----------
- コードは可能な限り副作用を抑え、外部呼び出しは注入可能（関数に接続やクライアントを渡す）な設計になっています。ユニットテスト作成時は外部 API 呼び出しをモック（unittest.mock.patch）してください。
- logging_setup はアプリケーション全体で統一して使ってください（setup_logging(app_name="...")）。

ライセンス・貢献
----------------
- この README では省略。実際のリポジトリに LICENSE ファイルを含めてください。

問い合わせ
----------
実装内容や設定について不明点があれば、どの機能について知りたいかを教えてください。具体的な起動コマンドや .env のテンプレート例も必要であれば提供します。