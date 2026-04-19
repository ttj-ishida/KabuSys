KabuSys — 日本株自動売買システム
=============================

このリポジトリは、個人向けの日本株自動売買システム（KabuSys）の一部実装です。
主に以下を含みます：注文実行エンジン（ExecutionEngine）、監視コンポーネント（Monitoring）、ポートフォリオ構築・リスク制御、研究用モジュール、AI（ニュース NLP）モジュール、各種ユーティリティ。

この README ではプロジェクト概要、主な機能、セットアップ手順、基本的な使い方、プロジェクト構成を日本語でまとめます。

プロジェクト概要
---------------
KabuSys は以下の機能を持つ自動売買フレームワークです（実装はモジュール単位で分離されています）：

- 注文実行（ExecutionEngine）:
  - 実口座（live）またはペーパートレード（paper_trading）切替可能
  - Broker クライアントは環境に応じて実ブローカー／モックを選択
  - リスク管理、オーダー管理、リコンサイル機能を組み込み

- 監視（Monitoring）:
  - SystemMonitor（CPU／メモリ／ディスク／データ鮮度／実行プロセス監視）
  - TradeMonitor / RiskMonitor による注文・ドローダウン・ポジション上限監視
  - Kill Switch（条件に達すると data/kill.flag を作成して Execution を停止）
  - 監視ログは SQLite（monitoring.db）へ永続化

- ポートフォリオ構築:
  - 候補選定・重み付け（等金額／スコア加重）
  - セクターキャップ／レジーム乗数
  - 株数決定（lot 単位・リスクベース / ウエイトベース 等）

- 研究用モジュール:
  - ファクター計算（Momentum / Value / Volatility 等）
  - 将来リターン計算・IC（Information Coefficient）評価・統計サマリ

- AI（ニュース NLP / レジーム判定）:
  - OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価
  - 銘柄別スコアやマクロセンチメントを用いた市場レジーム推定

- ツール:
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）
  - 対話式の .env 作成ウィザード・設定検証 CLI など

主な機能一覧
-------------
- Execution: ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading.db に記録
  - PID ファイル / stop フラグを使った起動・停止制御

- Monitoring: SystemMonitor を定期ポーリングして monitoring DB に記録（run_monitoring.py）
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 単体の MonitoringEngine（複数 Monitor をまとめてポーリング）も利用可能

- Config ユーティリティ:
  - 対話式 .env ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）

- Paper Trading レポート: tools/paper_verification_report にて注文成功率・稼働率・レイテンシ等の集計・判定

セットアップ手順
----------------

1. リポジトリをクローンし仮想環境を作る
   - 例:
     - git clone <repo>
     - python -m venv .venv
     - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 主な依存（抜粋）:
     - duckdb
     - psutil
     - openai
     - pyyaml（設定検証で YAML のパースを行う場合に任意）
   - 例:
     - pip install duckdb psutil openai pyyaml

   ※ sqlite3 は標準ライブラリに含まれます。

3. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または手動で .env を作成（プロジェクトルートに配置）
   - 必須の環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な設定（デフォルトがあるものも含む）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - DUCKDB_PATH — default: data/kabusys.duckdb
     - SQLITE_PATH — default: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（default: data/paper_trading.db）
     - LOG_LEVEL — default: INFO
     - OPENAI_API_KEY — AI モジュール使用時に必要
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 任意（アラート送信）

   - サンプル .env（最小）:
     JQUANTS_REFRESH_TOKEN=your_jquants_token_here
     KABU_API_PASSWORD=your_kabu_password_here
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱い（exit 1）

5. データ/ログディレクトリの作成（通常は自動で作成されますが事前に作る場合）
   - mkdir -p data logs

基本的な使い方
---------------

- ExecutionEngine を起動（本番またはペーパー）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を .env または環境で設定するとペーパートレード用 DB に記録され、MockBroker を使用します。
  - 実行中に data/stop_requested.flag を作成すると起動中スレッドにより停止処理が走ります（停止フラグの検出）。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト 60）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は settings.sqlite_path（通常 data/monitoring.db）へ書き込みます（Monitoring は環境に関係なく本番 sqlite_path を使用する設計）。

- Kill Switch（外部から停止を強制する）
  - KillSwitch は内部から条件を満たすと data/kill.flag を書き込みます。
  - 手動で停止させたい場合は実行中のプロセスに応じて stop_requested.flag または kill.flag を操作します。
    - 例: echo "reason" > data/kill.flag
  - Settings.kill_flag_clear_on_start を 1 にしていると起動時に既存の kill.flag を自動クリアします（本番では 0 推奨）。

- Paper Trading レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで SQLite DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI モジュール（ニューススコア／レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY 環境変数または関数引数）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime などを利用

ログ・DB の場所（デフォルト）
----------------------------
- DuckDB: data/kabusys.duckdb
- Monitoring SQLite: data/monitoring.db
- Paper Trading SQLite: data/paper_trading.db
- ログ: logs/<app_name>.log（setup_logging により daily rotate で保存、30 日保持）
- PID / フラグ:
  - data/execution.pid（ExecutionEngine の PID）
  - data/stop_requested.flag（手動停止フラグ）
  - data/kill.flag（Kill Switch フラグ）

注意点・運用上のヒント
---------------------
- 本番運用時は KABUSYS_ENV=live を使用します。validate_config は live の場合に追加の警告を出します（LINE 通知設定など）。
- ファイルベースで停止やフラグ管理を行う設計です。スクリプトをサービス化する場合は systemd 等でラップしてください。
- Paper Trading は本番 DB と分離されます（settings.is_paper が True のとき paper_sqlite_path を使用）。
- OpenAI を呼ぶ関数は外部 API 呼び出しに依存するため、API制限、コスト、応答失敗に注意してください。失敗時はフェイルセーフ（スコア 0.0 など）を採る実装になっています。
- ロギングは kabusys.utils.logging_setup.setup_logging で統一されています。ログディレクトリ作成に失敗した場合はコンソールのみ出力されます。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings 管理（自動 .env 読み込み機能含む）
- config_setup.py          — 対話式 .env 作成ウィザード
- validate_config.py       — 起動前設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

サブパッケージ（主なファイル）
- ai/
  - news_nlp.py             — ニュース NLP（OpenAI 呼び出し・スコア保存）
  - regime_detector.py      — マクロ + MA を組み合わせた市場レジーム判定
- monitoring/
  - monitoring_db.py        — SQLite による監視ログ永続化（schema/migration 含む）
  - system_monitor.py       — CPU/メモリ/ディスク/データ鮮度監視
  - risk_monitor.py         — ドローダウン / ポジション数監視
  - kill_switch.py          — kill.flag 管理
  - monitoring_engine.py    — 各 Monitor を束ねるエンジン
  - (TradeMonitor, AlertManager など参照あり)
- execution/
  - (broker_factory, execution_engine, order_manager, order_repository, risk_manager, reconciler 等)
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py
- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py
  - __init__.py
- monitoring/ (上記と同名フォルダ、監視関連)
- data/ (実行時に生成されるファイル: *.db, *.pid, *.flag)
- logs/ (ログファイル格納)

開発・テストに関する補足
-----------------------
- 自動で .env を読み込む仕様になっており、プロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を読みます。テスト等でこれを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 多くのモジュールは純粋関数（DB 参照なし）として実装されており、ユニットテストが容易な設計になっています。
- OpenAI API 呼び出し部分は内部でラップされており、ユニットテスト時は該当関数をモックして外部依存を切り離せます。

ライセンス・貢献
----------------
- （この README ではライセンス情報・コントリビューション手順は省略しています。必要に応じて追加してください。）

最後に
-------
ここに示したのはコードベースの主要な使い方と構成の要約です。実運用・デプロイ時は .env 設定や DB バックアップ、監視・再起動ポリシー、セキュリティ（API トークン管理）を必ず確認してください。必要であれば README に実行例・systemd ユニットや Dockerfile の記載を追加します — 追加希望があれば教えてください。