KabuSys — 日本株自動売買システム
================================

この README はリポジトリ内の主要スクリプト・ライブラリの使い方、セットアップ、ディレクトリ構成を日本語でまとめたドキュメントです。  
コードは src/kabusys 以下に配置されています。

プロジェクト概要
--------------
KabuSys は日本株の自動売買・リサーチ・監視を目的としたモジュール群です。主な機能は以下です。

- ExecutionEngine（売買実行エンジン） — ブローカークライアントを使った注文管理・発注・リスク管理
- Monitoring（監視） — システム稼働状況・注文ログ・リスク監視と Kill Switch の運用
- Portfolio（ポートフォリオ構築） — 候補選定、重み計算、ポジションサイズ計算、セクター制限
- Research（リサーチ） — ファクター計算、将来リターン・IC 計算、特徴量解析
- AI モジュール — ニュースを LLM でセンチメント化する news_nlp、レジーム判定 module
- Tools — ペーパートレード検証レポート生成などユーティリティ

主な特長
--------
- 環境変数 / .env による設定管理（config_setup による対話ウィザードあり）
- DuckDB（分析）と SQLite（監視／発注ログ）を併用
- Paper Trading 環境と Live 環境の分離（paper_trading 用の別 DB）
- OpenAI を利用した NLP（ニュースセンチメント）機能（API キー必要）
- ログを統一的に設定（stdout と日次ローテーションファイル）

機能一覧
--------
- 実行エンジン起動: src/kabusys/run_execution.py
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient（ペーパートレード）を使用し、data/paper_trading.db を使用
  - プロセス優先度設定、PID ファイル管理、停止フラグ検知（data/stop_requested.flag）
- 監視ループ起動: src/kabusys/run_monitoring.py
  - システム監視（CPU/メモリ/Disk）、データ鮮度、プロセス存在チェック等をポーリング
  - MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能（デフォルト 60）
  - 監視は環境にかかわらず本番 sqlite_path を使用
- 設定ウィザード: src/kabusys/config_setup.py
  - .env の初期作成・更新を対話形式で行う
- 設定検証 CLI: src/kabusys/validate_config.py
  - 必須環境変数や config/*.yaml の存在・YAML パースを検証。--strict モードあり
- Paper Trading 検証レポート: src/kabusys/tools/paper_verification_report.py
  - ペーパートレード用 SQLite を参照して稼働率・注文成功率・レイテンシ等を出力
- ポートフォリオ系ユーティリティ: src/kabusys/portfolio/*
  - 候補選定、等重・スコア重み、ポジションサイズ計算、セクターキャップ、レジーム乗数
- AI モジュール: src/kabusys/ai/*
  - news_nlp: OpenAI でニュースをスコア化して ai_scores に格納
  - regime_detector: MA200 とマクロニュースを組み合わせて日次レジーム判定
- 監視 DB 層: src/kabusys/monitoring/monitoring_db.py
  - system_status / trade_logs / positions / risk_logs / dashboard のテーブル作成と CRUD
- 共通ユーティリティ: src/kabusys/utils/*
  - ログ設定、プロセス優先度 / CPU affinity 設定など

セットアップ手順
----------------
以下はローカルで開発／実行するための一般的な手順です。

1. Python 環境
   - Python 3.9+ を推奨（使用ライブラリに依存）
   - 仮想環境を作成して有効化することを推奨:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリのインストール
   - 必須（プロジェクトの import から推定）:
     - duckdb, psutil, openai
   - オプション（YAML 検証など）:
     - PyYAML
   - 例:
     - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を使用）

3. .env の作成
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - 必須の環境変数（例）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 主要な環境変数とデフォルト:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO
     - OPENAI_API_KEY: OpenAI を使う場合に必要
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番アラート用（任意）
     - その他: PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, MONITOR_POLL_INTERVAL（監視ポーリング間隔）

4. DB の準備
   - 監視用 DB はスクリプト起動時にテーブルを作成（init_monitoring_db）するため、事前作成は必須ではありません。
   - DuckDB ファイルは分析用。prices_daily / raw_financials 等のテーブルはデータが必要。

使い方（主要なコマンド）
----------------------
- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定の事前検証
  - python -m kabusys.validate_config
  - 警告を厳格扱いにする: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用（本番 DB と分離）
    - 起動時に PID ファイルを書き、data/stop_requested.flag を監視して停止
    - プロセス優先度を high に設定（可能な場合）

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60）
  - 監視は常に settings.sqlite_path（監視用 DB）を使用

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI（ニュース NLP / レジーム判定）呼び出し
  - 各関数は DuckDB 接続と target_date を受け、OpenAI API キー（引数 or OPENAI_API_KEY 環境変数）を必要とします。
  - 例（ライブラリとして利用）:
    - from kabusys.ai.news_nlp import score_news
    - from kabusys.ai.regime_detector import score_regime

停止・Kill Switch
-----------------
- ExecutionEngine の停止:
  - data/stop_requested.flag をプロジェクトルートに作成すると、run_execution が検知して停止します（またはプロセスに SIGINT）。
- Kill Switch:
  - monitoring の KillSwitch は条件を満たすと data/kill.flag を書き込みます。Execution 起動時に Settings.kill_flag_clear_on_start が 1 であれば自動クリアされる点に注意（本番環境では 0 推奨）。

ログ
---
- ログは標準出力（stdout）と日次ローテートファイルに出力されます（デフォルト logs/<app_name>.log）。
- ログレベルは LOG_LEVEL 環境変数で変更可能。

重要な環境変数一覧（抜粋）
--------------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト data/paper_trading.db
- PAPER_FILL_MODE — paper_trading の約定動作: instant | partial | never | reject（デフォルト "instant"）
- OPENAI_API_KEY — AI 機能利用時に必要
- LOG_LEVEL — デフォルト INFO
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START

ディレクトリ構成
----------------
以下は src/kabusys 以下の主要ファイル・ディレクトリ構成の概略です（リポジトリルートに .env や data/、logs/ 等が想定されます）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (存在が想定される)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (存在が想定される)
  - execution/
    - ブローカーファクトリやエンジン、オーダー管理など（実装ファイル群）
  - data/  (ランタイムのファイル・ディレクトリを想定)
    - monitoring.db, paper_trading.db, stop_requested.flag, kill.flag, execution.pid など
  - utils/
    - logging_setup.py
    - process_priority.py

（注）一部ファイルはドキュメント内で参照されるがこのスニペットにすべて含まれていない場合があります（例: execution パッケージ内細部、alert_manager・trade_monitor 等）。実行前に該当モジュールが存在することを確認してください。

開発・運用上の注意
-----------------
- .env を絶対に Git にコミットしないこと（config_setup も README に警告文を出力します）。
- 本番（KABUSYS_ENV=live）では LINE 通知や Kill Switch 動作などを特に確認してください。validate_config は live 時の追加チェックを行います。
- OpenAI を使う機能は API コストやレート制限に注意してください（リトライ・バックオフ処理あり）。
- monitoring は監視用 DB（SQLITE_PATH）を常に参照します。開発時に monitoring が本番 DB を誤って参照しないようご注意ください。
- psutil を使ってプロセス優先度・CPU affinity を設定しますが、権限や OS 次第で動作しない場合があります（ログに警告が出ます）。

お問い合わせ / 参考
------------------
- 各モジュールのドキュメント（ソース内 docstring）を参照してください。関数・クラスには運用上の重要な注意や設計方針が記載されています。
- まずは:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config
  を順に実行して設定と環境を整えてください。

必要であれば README にサンプル .env のテンプレートや systemd / Supervisor 用のサービス定義例、Dockerfile などの運用ガイドを追記できます。追加したい内容があれば指示ください。